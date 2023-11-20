import glob
import os
import shutil
import time

from defusedxml.minidom import parse

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.utils import download_extract_zip, find_replace, find_replace_regex
from cumulusci.utils.options import (
    CCIOptions,
    DirectoryPath,
    Field,
    ListOfStringsOption,
)


class DownloadZip(BaseTask):
    name = "Download"

    class Options(CCIOptions):
        url: str = Field(..., description="The url of the zip file to download")
        dir: str = Field(
            ..., description="The directory where the zip should be extracted"
        )
        subfolder: str = Field(
            None,
            description=(
                "The subfolder of the target zip to extract. Defaults to"
                + " extracting the root of the zip file to the destination."
            ),
        )

    parsed_options: Options

    def _run_task(self):
        if not os.path.exists(self.parsed_options.dir):
            os.makedirs(self.parsed_options.dir)

        download_extract_zip(
            self.parsed_options.url,
            self.parsed_options.dir,
            self.parsed_options.subfolder,
        )


class ListMetadataTypes(BaseTask):
    name = "ListMetadataTypes"

    class Options(CCIOptions):
        package_xml: str = Field(
            None,
            description=(
                "The project package.xml file."
                + " Defaults to <project_root>/src/package.xml"
            ),
        )

    def _init_options(self, kwargs):
        super(ListMetadataTypes, self)._init_options(kwargs)
        if not self.parsed_options.get("package_xml"):
            self.parsed_options["package_xml"] = os.path.join(
                self.project_config.repo_root, "src", "package.xml"
            )

    def _run_task(self):
        dom = parse(self.parsed_options["package_xml"])
        package = dom.getElementsByTagName("Package")[0]
        types = package.getElementsByTagName("types")
        type_list = []
        for t in types:
            name = t.getElementsByTagName("name")[0]
            metadata_type = name.firstChild.nodeValue
            type_list.append(metadata_type)
        self.logger.info(
            "Metadata types found in %s:\r\n%s",
            self.parsed_options["package_xml"],
            "\r\n".join(type_list),
        )


class Sleep(BaseTask):
    name = "Sleep"

    class Options(CCIOptions):
        seconds: int = Field(..., description="The number of seconds to sleep")

    parsed_options: Options

    def _run_task(self):
        self.logger.info("Sleeping for {} seconds".format(self.parsed_options.seconds))
        time.sleep(float(self.parsed_options.seconds))
        self.logger.info("Done")


class Delete(BaseTask):
    name = "Delete"

    class Options(CCIOptions):
        path: ListOfStringsOption = Field(
            default=...,
            description=(
                "The path to delete. "
                "If path is a directory, recursively deletes the directory: BE CAREFUL!!! "
                "If path is a list, all paths will be deleted"
            ),
        )
        chdir: DirectoryPath = Field(
            default=None,
            description=(
                "Change directories before deleting path(s). "
                "This is useful if you have a common list of relative paths to "
                "delete that you want to call against different directories."
            ),
        )

    def _run_task(self):
        chdir = self.parsed_options.chdir
        cwd = os.getcwd()
        if chdir:
            self.logger.info("Changing directory to {}".format(chdir))
            os.chdir(chdir)

        path = self.parsed_options.path
        if not isinstance(path, list):
            path = [path]
        for path_item in path:
            matches = glob.glob(path_item)
            if matches:
                for match in matches:
                    self._delete(match)
            else:
                self.logger.info("{} does not exist, skipping delete".format(path))

        if chdir:
            os.chdir(cwd)

    def _delete(self, path):
        if os.path.isdir(path):
            self.logger.info("Recursively deleting directory {}".format(path))
            shutil.rmtree(path)
        else:
            self.logger.info("Deleting file {}".format(path))
            os.remove(path)


class FindReplaceOptions(CCIOptions):
    find: str = Field(..., description="The string to search for")
    replace: str = Field(
        "",
        description="The string to replace matches with. Defaults to an empty string",
    )
    path: DirectoryPath = Field(..., description="The path to recursively search")
    file_pattern: ListOfStringsOption = Field(
        "*",
        description="A UNIX like filename pattern used for matching filenames, or a list of them. See python fnmatch docs for syntax. If passed via command line, use a comma separated string. Defaults to *",
    )
    env_replace: bool = Field(
        False,
        description="If True, treat the value of the replace option as the name of an environment variable, and use the value of that variable as the replacement string. Defaults to False",
    )


class FindReplace(BaseTask):
    class Options(FindReplaceOptions):
        max: int = Field(
            None,
            description="The max number of matches to replace.  Defaults to replacing all matches.",
        )

    parsed_options: Options

    def _run_task(self):
        kwargs = {}
        if self.parsed_options.max:
            kwargs["max"] = self.parsed_options.max

        if self.parsed_options["env_replace"]:
            if self.parsed_options["replace"] in os.environ.keys():
                self.parsed_options["replace"] = os.environ[
                    self.parsed_options["replace"]
                ]
            else:
                raise TaskOptionsError(
                    f"The environment variable {self.parsed_options['replace']} was not found. Ensure that this value is populated or set env_replace to False."
                )

        for file_pattern in self.parsed_options["file_pattern"]:
            find_replace(
                find=self.parsed_options.find,
                replace=self.parsed_options.replace,
                directory=self.parsed_options.path,
                filePattern=file_pattern,
                logger=self.logger,
                **kwargs,
            )


class FindReplaceRegex(FindReplace):
    class Options(FindReplaceOptions):
        pass

    def _run_task(self):
        find_replace_regex(
            find=self.parsed_options.find,
            replace=self.parsed_options.replace,
            directory=self.parsed_options.path,
            filePattern=self.parsed_options.file_pattern,
            logger=self.logger,
        )


class CopyFile(BaseTask):
    task_options = {
        "src": {"description": "The path to the source file to copy", "required": True},
        "dest": {
            "description": "The destination path where the src file should be copied",
            "required": True,
        },
    }

    def _run_task(self):
        self.logger.info("Copying file {src} to {dest}".format(**self.options))
        shutil.copyfile(src=self.options["src"], dst=self.options["dest"])


class LogLine(BaseTask):
    task_options = {
        "level": {"description": "The logger level to use", "required": True},
        "line": {"description": "A formatstring like line to log", "required": True},
        "format_vars": {"description": "A Dict of format vars", "required": False},
    }

    def _init_options(self, kwargs):
        super(LogLine, self)._init_options(kwargs)
        if "format_vars" not in self.options:
            self.options["format_vars"] = {}

    def _run_task(self):
        log = getattr(self.logger, self.options["level"])
        log(self.options["line"].format(**self.options["format_vars"]))


class PassOptionAsResult(BaseTask):
    task_options = {
        "result": {"description": "The result for the task", "required": True}
    }

    def _run_task(self):
        return self.options["result"]


class PassOptionAsReturnValue(BaseTask):
    task_options = {
        "key": {"required": True, "description": "The return value key to use."},
        "value": {"required": True, "description": "The value to set."},
    }

    def _run_task(self):
        self.return_values[self.options["key"]] = self.options["value"]
