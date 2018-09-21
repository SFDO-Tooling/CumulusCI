from cumulusci.core.exceptions import ApexCompilationException
from cumulusci.core.exceptions import ApexException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import in_directory


class AnonymousApexTask(BaseSalesforceApiTask):
    """ Executes anonymous apex from a file or string."""

    task_docs = """
    Use the `apex` option to run a string of anonymous Apex.
    Use the `path` option to run anonymous Apex from a file.
    Or use both to concatenate the string to the file contents.
    """

    task_options = {
        "path": {"description": "The path to an Apex file to run.", "required": False},
        "apex": {
            "description": "A string of Apex to run (after the file, if specified).",
            "required": False,
        },
        "managed": {
            "description": (
                "If True, will insert the project's namespace prefix.  "
                "Defaults to False or no namespace."
            ),
            "required": False,
        },
        "namespaced": {
            "description": (
                "If True, the tokens %%%NAMESPACED_RT%%% and %%%namespaced%%% "
                "will get replaced with the namespace prefix for Record Types."
            ),
            "required": False,
        },
    }

    def _validate_options(self):
        super(AnonymousApexTask, self)._validate_options()

        if not self.options.get("path") and not self.options.get("apex"):
            raise TaskOptionsError(
                "You must specify either the `path` or `apex` option."
            )

    def _run_task(self):
        apex = ""
        apex_path = self.options.get("path")
        if apex_path:
            if not in_directory(apex_path, self.project_config.repo_root):
                raise TaskOptionsError(
                    "Please specify a path inside your project repository. "
                    "You specified: {}".format(apex_path)
                )
            self.logger.info("Executing anonymous Apex from {}".format(apex_path))
            try:
                with open(apex_path, "r") as f:
                    apex = f.read()
            except IOError:
                raise TaskOptionsError(
                    "Could not find or read file: {}".format(apex_path)
                )
        else:
            self.logger.info("Executing anonymous Apex")

        apex_string = self.options.get("apex")
        if apex_string:
            apex = apex + "\n" + apex_string

        apex = self._prepare_apex(apex)
        result = self.tooling._call_salesforce(
            method="GET",
            url="{}executeAnonymous".format(self.tooling.base_url),
            params={"anonymousBody": apex},
        )
        self._check_result(result)

        self.logger.info("Anonymous Apex Success")

    def _prepare_apex(self, apex):
        # Process namespace tokens
        managed = self.options.get("managed") or False
        namespaced = self.options.get("namespaced") or False
        namespace = self.project_config.project__package__namespace
        namespace_prefix = ""
        record_type_prefix = ""
        if managed or namespaced:
            namespace_prefix = namespace + "__"
        if namespaced:
            record_type_prefix = namespace + "."
        apex = apex.replace("%%%NAMESPACE%%%", namespace_prefix)
        apex = apex.replace("%%%NAMESPACED_ORG%%%", namespace_prefix)
        apex = apex.replace("%%%NAMESPACED_RT%%%", record_type_prefix)

        return apex

    def _check_result(self, result):
        # anon_results is an ExecuteAnonymous Result
        # https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/sforce_api_calls_executeanonymous_result.htm
        anon_results = result.json()
        if not anon_results["compiled"]:
            raise ApexCompilationException(
                anon_results["line"], anon_results["compileProblem"]
            )
        if not anon_results["success"]:
            raise ApexException(
                anon_results["exceptionMessage"], anon_results["exceptionStackTrace"]
            )
