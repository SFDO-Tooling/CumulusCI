from cumulusci.core.exceptions import (
    ApexCompilationException,
    ApexException,
    SalesforceException,
    TaskOptionsError,
)
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import in_directory, inject_namespace
from cumulusci.utils.http.requests_utils import safe_json_from_response


class AnonymousApexTask(BaseSalesforceApiTask):
    """Executes anonymous apex from a file or string."""

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
        "param1": {
            "description": (
                "Parameter to pass to the Apex. Use as %%%PARAM_1%%% in the Apex code. "
                "Defaults to an empty value."
            ),
            "required": False,
        },
        "param2": {
            "description": (
                "Parameter to pass to the Apex. Use as %%%PARAM_2%%% in the Apex code. "
                "Defaults to an empty value."
            ),
            "required": False,
        },
    }

    def _validate_options(self):
        super()._validate_options()

        if not self.options.get("path") and not self.options.get("apex"):
            raise TaskOptionsError(
                "You must specify either the `path` or `apex` option."
            )

    def _run_task(self):
        apex = self._process_apex_from_path(self.options.get("path"))
        apex += self._process_apex_string(self.options.get("apex"))

        apex = self._prepare_apex(apex)
        self.logger.info("Executing anonymous Apex")
        result = self.tooling._call_salesforce(
            method="GET",
            url=f"{self.tooling.base_url}executeAnonymous",
            params={"anonymousBody": apex},
        )
        self._check_result(result)
        self.logger.info("Anonymous Apex Executed Successfully!")

    def _process_apex_from_path(self, apex_path):
        """Process apex given via the --path task option"""
        if not apex_path:
            return ""
        if not in_directory(apex_path, self.project_config.repo_root):
            raise TaskOptionsError(
                "Please specify a path inside your project repository. "
                f"You specified: {apex_path}"
            )
        self.logger.info(f"Processing Apex from path: {apex_path}")
        try:
            with open(apex_path, "r", encoding="utf-8") as f:
                apex = f.read()
        except IOError:
            raise TaskOptionsError(f"Could not find or read file: {apex_path}")
        return apex

    def _process_apex_string(self, apex_string):
        """Process the string of apex given via the --apex task option"""
        apex = ""
        if apex_string:
            self.logger.info("Processing Apex from '--apex' option")
            # append a newline so that we don't clash if
            # apex was also given via the --path option
            apex = "\n" + apex_string
        return apex

    def _prepare_apex(self, apex):
        # Process namespace tokens
        namespace = self.project_config.project__package__namespace
        if "managed" in self.options:
            managed = process_bool_arg(self.options["managed"])
        else:
            managed = (
                bool(namespace) and namespace in self.org_config.installed_packages
            )
        if "namespaced" in self.options:
            namespaced = process_bool_arg(self.options["namespaced"])
        else:
            namespaced = bool(namespace) and namespace == self.org_config.namespace

        _, apex = inject_namespace(
            "",
            apex,
            namespace=namespace,
            managed=managed,
            namespaced_org=namespaced,
        )

        # This is an extra token which is not handled by inject_namespace.
        apex = apex.replace(
            "%%%NAMESPACED_RT%%%", namespace + "." if namespaced else ""
        )

        # Process optional parameter token replacement
        param1 = self.options.get("param1") or ""
        apex = apex.replace("%%%PARAM_1%%%", param1)
        param2 = self.options.get("param2") or ""
        apex = apex.replace("%%%PARAM_2%%%", param2)

        return apex

    def _check_result(self, result):
        # anon_results is an ExecuteAnonymous Result
        # https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/sforce_api_calls_executeanonymous_result.htm
        anon_results = safe_json_from_response(result)

        # A result of `None` (body == "null") with a 200 status code means that a gack occurred.
        if anon_results is None:
            raise SalesforceException(
                "Anonymous Apex returned the result `null`. "
                "This often indicates a gack occurred."
            )
        if not anon_results["compiled"]:
            raise ApexCompilationException(
                anon_results["line"], anon_results["compileProblem"]
            )
        if not anon_results["success"]:
            raise ApexException(
                anon_results["exceptionMessage"], anon_results["exceptionStackTrace"]
            )
