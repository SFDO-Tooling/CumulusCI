import json
import random
import re
import string
from pathlib import Path

from cumulusci.cli.ui import CliTable
from cumulusci.core.exceptions import SalesforceException
from cumulusci.core.utils import determine_managed_mode, process_list_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import inject_namespace

API_ROLLBACK_MESSAGE = "The transaction was rolled back since another operation in the same transaction failed."
API_INVALID_REF_MESSAGE = "Invalid reference specified."


class CompositeApi(BaseSalesforceApiTask):
    task_docs = """
This task is a wrapper for Composite REST API calls. Given a list of JSON files
(one request body per file), POST each and process the returned composite
result. Files are processed in the order given by the ``data_files`` option.

In addition, this task will process the request body and replace namespace
(``%%%NAMESPACE%%%``) and user ID (``%%%USERID%%%``) tokens. To avoid username
collisions, use the ``randomize_username`` option to replace the top-level
domains in any ``Username`` field with a random string.

When the top-level ``allOrNone`` property for the request is set to true a
SalesforceException is raised if an error is returned for any subrequest,
otherwise partial successes will not raise an exception.

Example Task Definition
-----------------------

.. code-block::  yaml

  tasks:
      example_composite_request:
          class_path: cumulusci.tasks.salesforce.composite.CompositeApi
          options:
             data_files:
                 - "datasets/composite/users.json"
                 - "datasets/composite/setup_objects.json"
    """

    task_options = {
        "data_files": {
            "description": "A list of paths, where each path is a JSON file containing a composite request body.",
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

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.data_files = process_list_arg(self.options.get("data_files") or [])

    def _run_task(self):
        for data_file_path in self.data_files:
            self.logger.info(f"Processing {data_file_path}")
            self._composite_request(data_file_path)

    def _composite_request(self, data_file_path):
        request_body = self._process_json(Path(data_file_path).read_text())
        self.is_all_or_none = json.loads(request_body).get("allOrNone", False)
        result = self.sf.restful("composite", method="POST", data=request_body)
        self._process_response(result)

    def _process_json(self, body):
        """Replace namespace tokens and randomize username domains."""
        user_id = self.org_config.user_id
        body = body.replace("%%%USERID%%%", user_id)

        namespace = self.project_config.project__package__namespace
        managed = determine_managed_mode(
            self.options, self.project_config, self.org_config
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
                r'("Username": .[\w-]+@[\w-]+\.)+[\w-]+', rf"\1{random_tld}", body
            )

        return body

    def _process_response(self, result):
        """Handle the compositeResponse and raise an exception if failed."""
        subrequests = result["compositeResponse"]
        status_codes = {subrequest["httpStatusCode"] for subrequest in subrequests}

        all_success = all([self._http_ok(code) for code in status_codes])
        if self.is_all_or_none and not all_success:
            self._log_exception_message(subrequests)
            raise SalesforceException(json.dumps(subrequests, indent=2))
        else:
            self._log_success_message(subrequests)

    def _http_ok(self, status_code):
        return status_code >= 200 and status_code < 300

    def _log_exception_message(self, subrequests):
        table_data = [["ReferenceId", "Message"]]
        table_data.extend(
            [sub["referenceId"], body["message"]]
            for sub in subrequests
            for body in sub["body"]
            if body.get("message") != API_ROLLBACK_MESSAGE
        )
        table = CliTable(
            table_data,
        )
        self.logger.error("The request failed with the following message(s):\n\n")
        table.echo()

    def _log_success_message(self, subrequests):
        table_data = [["ReferenceId", "Success"]]
        table_data.extend(
            [sub["referenceId"], self._http_ok(sub["httpStatusCode"])]
            for sub in subrequests
        )
        table = CliTable(table_data, title="Subrequest Results")
        table.echo()
