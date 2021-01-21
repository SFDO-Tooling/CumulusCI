import json
import random
import re
import string
from pathlib import Path

from cumulusci.cli.ui import CliTable
from cumulusci.core.exceptions import SalesforceException
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import inject_namespace

API_ROLLBACK_MESSAGE = "The transaction was rolled back since another operation in the same transaction failed."
API_INVALID_REF_MESSAGE = "Invalid reference specified."


class CompositeApi(BaseSalesforceApiTask):
    """
    Wrapper for Composite REST API calls.

    Replaces "%%%USERID%%%" and namespace tokens with the running user's
    ID and project namespace, respectively. Replaces any usernames that include
    the "connected.edu" domain with a random TLD.
    """

    task_options = {
        "data_files": {
            "description": "A list of paths to the json files to POST.",
            "required": True,
        },
        "managed": {
            "description": "If True, replaces namespace tokens with the namespace prefix.",
            "default": False,
        },
        "namespaced": {
            "description": "If True, replaces namespace tokens with the namespace prefix.",
            "default": False,
        },
        "randomize_username": {
            "description": "If True, randomize the TLD for any 'Username' fields.",
            "default": False,
        },
    }

    def _run_task(self):
        for data_file_path in self.options["data_files"]:
            self.logger.info(f"Processing {data_file_path}")
            self._composite_request(data_file_path)

    def _composite_request(self, data_file_path):
        request_body = self._process_json(Path(data_file_path).read_text())
        self.is_all_or_none = json.loads(request_body)["allOrNone"]
        client = self._init_api()
        result = client.restful("composite", method="POST", data=request_body)
        self._process_response(result)

    def _process_json(self, body):
        """Replace namespace tokens and randomize username domains."""
        user_id = self.org_config.user_id
        body = body.replace("%%%USERID%%%", user_id)

        namespace = self.project_config.project__package__namespace
        if "managed" in self.options:
            managed = process_bool_arg(self.options["managed"])
        else:
            managed = (
                bool(namespace) and namespace in self.org_config.installed_packages
            )

        _, body = inject_namespace(
            "composite",
            body,
            namespace=namespace,
            managed=managed,
            namespaced_org=self.options.get("namespaced", self.org_config.namespaced),
        )

        if self.options.get("randomize_username", False):
            random_tld = "".join(random.choices(string.ascii_lowercase, k=4))
            body = re.sub(
                r'("Username": .[\w-]+@[\w-]+\.)+[\w-]+', fr"\1{random_tld}", body
            )

        return body

    def _process_response(self, result):
        """Handle the compositeResponse and raise an exception if failed."""
        subrequests = result["compositeResponse"]
        status_codes = {subrequest["httpStatusCode"] for subrequest in subrequests}

        all_success = all([self._http_ok(code) for code in status_codes])
        if self.is_all_or_none and not all_success:
            self._format_exception_message(subrequests)
            raise SalesforceException(json.dumps(subrequests, indent=2))
        else:
            self._format_success_message(subrequests)

    def _http_ok(self, status_code):
        return status_code >= 200 and status_code < 300

    def _format_exception_message(self, subrequests):
        table_data = [["ReferenceId", "Message"]]
        table_data.extend(
            [sub["referenceId"], body["message"]]
            for sub in subrequests
            for body in sub["body"]
            if body.get("message") != API_ROLLBACK_MESSAGE
        )
        table = CliTable(table_data, wrap_cols=["Message"])
        self.logger.error("The request failed with the following message(s):\n\n")
        table.echo()

    def _format_success_message(self, subrequests):
        table_data = [["ReferenceId", "Success"]]
        table_data.extend(
            [sub["referenceId"], self._http_ok(sub["httpStatusCode"])]
            for sub in subrequests
        )
        table = CliTable(table_data, bool_cols=["Success"], title="Subrequest Results")
        table.echo()
