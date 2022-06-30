import glob
import os
import shutil
import time
from xml.dom.minidom import parse

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseSalesforceTask, BaseTask
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.config import TaskConfig
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.utils import download_extract_zip, find_replace, find_replace_regex


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
        "env_replace": {
            "description": "If True, treat the value of the replace option as the name of an environment variable, and use the value of that variable as the replacement string. Defaults to False",
            "required": False,
        },
        "path": {"description": "The path to recursively search", "required": True},
        "file_pattern": {
            "description": "A UNIX like filename pattern used for matching filenames, or a list of them. See python fnmatch docs for syntax. If passed via command line, use a comma separated string. Defaults to *"
        },
        "max": {
            "description": "The max number of matches to replace.  Defaults to replacing all matches."
        },
    }

    def _init_options(self, kwargs):
        super(FindReplace, self)._init_options(kwargs)

        if "replace" not in self.options:
            self.options["replace"] = ""
        self.options["file_pattern"] = process_list_arg(
            self.options.get("file_pattern") or "*"
        )
        self.options["env_replace"] = process_bool_arg(
            self.options.get("env_replace") or False
        )

    def _run_task(self):
        kwargs = {}
        if "max" in self.options:
            kwargs["max"] = self.options["max"]

        if self.options["env_replace"]:
            if self.options["replace"] in os.environ.keys():
                self.options["replace"] = os.environ[self.options["replace"]]
            else:
                raise TaskOptionsError(
                    f"The environment variable {self.options['replace']} was not found. Ensure that this value is populated or set env_replace to False."
                )

        for file_pattern in self.options["file_pattern"]:
            find_replace(
                find=self.options["find"],
                replace=self.options["replace"],
                directory=self.options["path"],
                filePattern=file_pattern,
                logger=self.logger,
                **kwargs,
            )


find_replace_regex_options = FindReplace.task_options.copy()
del find_replace_regex_options["max"]


class FindReplaceRegex(FindReplace):
    task_options = find_replace_regex_options

    def _run_task(self):
        find_replace_regex(
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


class InjectMetaDataValueLWC(BaseSalesforceTask):
    """This class is used for the injection of variables at run time."""

    task_options = {
        "path": {
            "description": "Metadata API version to use, if not project__package__api_version.",
            "required": True,
        },
        "find": {
            "description": "Value to be replaced with within a file",
            "required": True,
        },
        "env_var": {
            "description": "Represents the value to replace the find variable in the file",
            "required": False,
        },
        "literal_var": {
            "description": "Represents the value to replace the find variable in the file",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.api_version = (
            self.options.get("api_version")
            or self.project_config.project__package__api_version
        )

        if any(["path" not in self.options, "find" not in self.options]):
            raise TaskOptionsError("Please check your options passed in.")
        self.options["literal_var"] = f"{self.org_config.instance_url}"
        self.options["replace"] = f"{self.org_config.instance_url}".replace(
            ".my.salesforce.com", ".lightning.force.com"
        )

    def _run_task(self):
        task_config = TaskConfig({"options": self.options})
        task = FindReplace(self.project_config, task_config, self.org_config)
        task()


class InjectMetaDataValueVisualForce(BaseSalesforceTask):
    """This class is used for the injection of variables at run time."""

    task_options = {
        "path": {
            "description": "Metadata API version to use, if not project__package__api_version.",
            "required": True,
        },
        "find": {
            "description": "Value to be replaced with within a file",
            "required": True,
        },
        "env_var": {
            "description": "Represents the value to replace the find variable in the file",
            "required": False,
        },
        "literal_var": {
            "description": "Represents the value to replace the find variable in the file",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.api_version = (
            self.options.get("api_version")
            or self.project_config.project__package__api_version
        )

        if any(["path" not in self.options, "find" not in self.options]):
            raise TaskOptionsError("Please check your options passed in.")
        self.options["literal_var"] = f"{self.org_config.instance_url}"
        self.options["replace"] = f"{self.org_config.instance_url}".replace(
            ".my.salesforce.com",
            f"--omnistudio.{self.org_config.instance_name}.visual.force.com",
        )

    def _run_task(self):
        task_config = TaskConfig({"options": self.options})
        task = FindReplace(self.project_config, task_config, self.org_config)
        task()
