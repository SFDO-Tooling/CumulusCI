""" a task for waiting on a specific custom settings value """

from simple_salesforce.exceptions import SalesforceError

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import determine_managed_mode, process_bool_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class CustomSettingValueWait(BaseSalesforceApiTask):
    """CustomSettingValueWait polls an org until the specific value exists in a custom settings field"""

    name = "CustomSettingValueWait"

    task_options = {
        "object": {
            "description": "Name of the Hierarchical Custom Settings object to query. Can include the %%%NAMESPACE%%% token. ",
            "required": True,
        },
        "field": {
            "description": "Name of the field on the Custom Settings to query. Can include the %%%NAMESPACE%%% token. ",
            "required": True,
        },
        "value": {
            "description": "Value of the field to wait for (String, Integer or Boolean). ",
            "required": True,
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
                "If True, the %%%NAMESPACE%%% token "
                "will get replaced with the namespace prefix for the object and field."
                "Defaults to False."
            ),
            "required": False,
        },
        "poll_interval": {
            "description": (
                "Seconds to wait before polling for batch job completion. "
                "Defaults to 10 seconds."
            )
        },
    }

    def _run_task(self):
        self.poll_interval_s = int(self.options.get("poll_interval", 10))

        # Retrieve polling object/field/value options
        self.object_name = self.options["object"]
        self.field_name = self.options["field"]
        self.check_value = self.options["value"]

        # Process namespace tokens
        self._apply_namespace()

        # will block until poll_complete
        self._poll()

        self.logger.info("Value Matched.")

        return True

    def _poll_action(self):
        try:
            query_results = self.sf.query(self._object_query)
        except SalesforceError as e:
            message = e.content[0]["message"]
            if "No such column 'SetupOwnerId'" in message:
                message = "Only Hierarchical Custom Settings objects are supported."
            raise TaskOptionsError(f"Query Error: {message}")

        self.record = None
        for row in query_results["records"]:
            if row["SetupOwnerId"].startswith("00D"):
                self.record = row

        if self.record:
            self.poll_complete = not self._poll_again()
        else:
            self.logger.info(
                f"{self.field_name}: Looking for {self.check_value} and found no custom settings record"
            )

    def _poll_again(self):
        return not self.success

    def _apply_namespace(self):
        # Process namespace tokens
        namespace = self.project_config.project__package__namespace
        managed = determine_managed_mode(
            self.options, self.project_config, self.org_config
        )
        if "namespaced" in self.options:
            namespaced = process_bool_arg(self.options["namespaced"])
        else:
            namespaced = bool(namespace) and self.org_config.namespace == namespace

        namespace_prefix = ""
        if namespace and (managed or namespaced):
            namespace_prefix = namespace + "__"
        self.object_name = self.object_name.replace("%%%NAMESPACE%%%", namespace_prefix)
        self.field_name = self.field_name.replace("%%%NAMESPACE%%%", namespace_prefix)

    @property
    def success(self):
        lower_case_record = {k.lower(): v for k, v in self.record.items()}
        self.field_value = lower_case_record[self.field_name.lower()]

        if isinstance(self.field_value, bool):
            self.check_value = process_bool_arg(self.check_value)
            self.field_value = process_bool_arg(self.field_value)
        elif isinstance(self.field_value, (int, float)):
            self.check_value = float(self.check_value)
            self.field_value = float(self.field_value)
        elif isinstance(self.field_value, str):
            self.check_value = str(self.check_value).lower()
            self.field_value = str(self.field_value).lower()

        self.logger.info(
            f"{self.field_name}: Looking for {self.check_value} and found {self.field_value}"
        )
        return self.field_value == self.check_value

    @property
    def _object_query(self):
        return f"SELECT SetupOwnerId, {self.field_name} FROM {self.object_name}"
