import os
import shutil
import time
import glob
from xml.dom.minidom import parse

from cumulusci.core.tasks import BaseTask
from cumulusci.utils import download_extract_zip, findReplace, findReplaceRegex


class DownloadZip(BaseTask):
    name = "Download"
    task_options = {
        "url": {"description": "The url of the zip file to download", "required": True},
        "dir": {
            "description": "The directory where the zip should be extracted",
            "required": True,
        },
        "subfolder": {
            "description": (
                "The subfolder of the target zip to extract. Defaults to"
                + " extracting the root of the zip file to the destination."
            )
        },
    }

    def _run_task(self):
        if not os.path.exists(self.options["dir"]):
            os.makedirs(self.options["dir"])

        download_extract_zip(
            self.options["url"], self.options["dir"], self.options.get("subfolder")
        )


class ListMetadataTypes(BaseTask):
    name = "ListMetadataTypes"
    task_options = {
        "package_xml": {
            "description": (
                "The project package.xml file."
                + " Defaults to <project_root>/src/package.xml"
            )
        }
    }

    def _init_options(self, kwargs):
        super(ListMetadataTypes, self)._init_options(kwargs)
        if "package_xml" not in self.options:
            self.options["package_xml"] = os.path.join(
                self.project_config.repo_root, "src", "package.xml"
            )

    def _run_task(self):
        dom = parse(self.options["package_xml"])
        package = dom.getElementsByTagName("Package")[0]
        types = package.getElementsByTagName("types")
        type_list = []
        for t in types:
            name = t.getElementsByTagName("name")[0]
            metadata_type = name.firstChild.nodeValue
            type_list.append(metadata_type)
        self.logger.info(
            "Metadata types found in %s:\r\n%s",
            self.options["package_xml"],
            "\r\n".join(type_list),
        )


class Sleep(BaseTask):
    name = "Sleep"
    task_options = {
        "seconds": {"description": "The number of seconds to sleep", "required": True}
    }

    def _run_task(self):
        self.logger.info("Sleeping for {} seconds".format(self.options["seconds"]))
        time.sleep(float(self.options["seconds"]))
        self.logger.info("Done")


class Delete(BaseTask):
    name = "Delete"
    task_options = {
        "path": {
            "description": "The path to delete.  If path is a directory, recursively deletes the directory: BE CAREFUL!!!  If path is a list, all paths will be deleted",
            "required": True,
        },
        "chdir": {
            "description": "Change directories before deleting path(s).  This is useful if you have a common list of relative paths to delete that you want to call against different directories."
        },
    }

    def _run_task(self):
        chdir = self.options.get("chdir")
        cwd = os.getcwd()
        if chdir:
            self.logger.info("Changing directory to {}".format(chdir))
            os.chdir(chdir)

        path = self.options["path"]
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


class FindReplace(BaseTask):
    task_options = {
        "find": {"description": "The string to search for", "required": True},
        "replace": {
            "description": "The string to replace matches with. Defaults to an empty string",
            "required": True,
        },
        "path": {"description": "The path to recursively search", "required": True},
        "file_pattern": {
            "description": "A UNIX like filename pattern used for matching filenames.  See python fnmatch docs for syntax.  Defaults to *",
            "required": True,
        },
        "max": {
            "description": "The max number of matches to replace.  Defaults to replacing all matches."
        },
    }

    def _init_options(self, kwargs):
        super(FindReplace, self)._init_options(kwargs)
        if "replace" not in self.options:
            self.options["replace"] = ""
        if "file_pattern" not in self.options:
            self.options["file_pattern"] = "*"

    def _run_task(self):
        kwargs = {}
        if "max" in self.options:
            kwargs["max"] = self.options["max"]
        findReplace(
            find=self.options["find"],
            replace=self.options["replace"],
            directory=self.options["path"],
            filePattern=self.options["file_pattern"],
            logger=self.logger,
            **kwargs
        )


find_replace_regex_options = FindReplace.task_options.copy()
del find_replace_regex_options["max"]


class FindReplaceRegex(FindReplace):
    task_options = find_replace_regex_options

    def _run_task(self):
        findReplaceRegex(
            find=self.options["find"],
            replace=self.options["replace"],
            directory=self.options["path"],
            filePattern=self.options["file_pattern"],
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
