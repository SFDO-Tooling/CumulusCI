from future import standard_library

standard_library.install_aliases()
import os
import tempfile
import urllib.request

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.command import Command


class GenerateApexDocs(Command):
    """ Generate Apex documentation from local code """

    apexdoc_repo_url = "https://github.com/SalesforceFoundation/ApexDoc"
    jar_file = "apexdoc.jar"
    task_options = {
        "tag": {
            "description": "The tag to use for links back to the repo. If "
            + "not provided, source_url arg to ApexDoc is omitted."
        },
        "source_directory": {
            "description": "The folder location which contains your apex "
            + ".cls classes. default=<RepoRoot>/src/classes/"
        },
        "out_dir": {
            "description": "The folder location where documentation will be "
            + "generated to. Defaults to project config value "
            + "project/apexdoc/dir if present, otherwise uses repo root."
        },
        "home_page": {
            "description": "The full path to an html file that contains the "
            + "contents for the home page's content area. Defaults to project "
            + "config value project/apexdoc/homepage if present, otherwise is "
            + "not used."
        },
        "banner_page": {
            "description": "The full path to an html file that contains the "
            + "content for the banner section of each generated page. "
            + "Defaults to project config value project/apexdoc/banner if "
            + "present, otherwise is not used."
        },
        "scope": {
            "description": "A semicolon separated list of scopes to "
            + "document. Defaults to project config value "
            + "project/apexdoc/scope if present, otherwise allows ApexDoc to "
            + "use its default (global;public;webService)."
        },
        "version": {
            "description": "Version of ApexDoc to use. Defaults to project "
            + "config value project/apexdoc/version."
        },
    }

    def _init_options(self, kwargs):
        super(GenerateApexDocs, self)._init_options(kwargs)
        self.options["command"] = None
        if "source_directory" not in self.options:
            self.options["source_directory"] = os.path.join(
                self.project_config.repo_root, "src", "classes"
            )
        if "out_dir" not in self.options:
            self.options["out_dir"] = (
                self.project_config.project__apexdoc__dir
                if self.project_config.project__apexdoc__dir
                else self.project_config.repo_root
            )
        if "tag" not in self.options:
            self.options["tag"] = None
        if "home_page" not in self.options:
            self.options["home_page"] = (
                self.project_config.project__apexdoc__homepage
                if self.project_config.project__apexdoc__homepage
                else None
            )
        if "banner_page" not in self.options:
            self.options["banner_page"] = (
                self.project_config.project__apexdoc__banner
                if self.project_config.project__apexdoc__banner
                else None
            )
        if "scope" not in self.options:
            self.options["scope"] = (
                self.project_config.project__apexdoc__scope
                if self.project_config.project__apexdoc__scope
                else None
            )
        if "version" not in self.options:
            if not self.project_config.project__apexdoc__version:
                raise CumulusCIException("ApexDoc version required")
            self.options["version"] = self.project_config.project__apexdoc__version

    def _init_task(self):
        super(GenerateApexDocs, self)._init_task()
        self.working_dir = tempfile.mkdtemp()
        self.jar_path = os.path.join(self.working_dir, self.jar_file)
        if self.options["tag"] and not self.project_config.project__git__repo_url:
            raise CumulusCIException("Repo URL not found in cumulusci.yml")

    def _run_task(self):
        self._get_jar()
        cmd = "java -jar {} -s {} -t {}".format(
            self.jar_path, self.options["source_directory"], self.options["out_dir"]
        )
        if self.options["tag"]:
            cmd += " -g {}/blob/{}/src/classes/".format(
                self.project_config.project__git__repo_url, self.options["tag"]
            )
        if self.options["home_page"]:
            cmd += " -h {}".format(self.options["home_page"])
        if self.options["banner_page"]:
            cmd += " -a {}".format(self.options["banner_page"])
        if self.options["scope"]:
            cmd += ' -p "{}"'.format(self.options["scope"])
        self.options["command"] = cmd
        self._run_command({})

    def _get_jar(self):
        url = "{}/releases/download/{}/{}".format(
            self.apexdoc_repo_url, self.options["version"], self.jar_file
        )
        urllib.request.urlretrieve(url, self.jar_path)
