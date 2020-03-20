""" a task for waiting on a specific custom settings value """

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.utils import process_bool_arg


class CustomSettingValueWait(BaseSalesforceApiTask):
    """ CustomSettingValueWait polls an org until the specific value exists in a custom settings field """

    name = "CustomSettingValueWait"

    task_options = {
        "object": {
            "description": "Name of the SObject to query. Can include the %%%NAMESPACE%%% token. ",
            "required": True,
        },
        "field": {
            "description": "Name of the field on the Sobject to query. Can include the %%%NAMESPACE%%% token. ",
            "required": True,
        },
        "value": {
            "description": "Value of the field to wait for (String or Boolean). ",
            "required": True,
        },
        "managed": {
            "description": (
                "If True, will inject the project's namespace prefix to replace %%%NAMESPACE%%% tokens in the object or field "
                "Defaults to False or no namespace."
            ),
            "required": False,
        },
        "poll_interval": {
            "description": (
                "Seconds to wait before polling for batch job completion. "
                "Defaults to 10 seconds."
            ),
        },
    }

    def _run_task(self):
        self.poll_interval_s = int(self.options.get("poll_interval", 10))

        self.object_name = self.options["object"]
        self.field_name = self.options["field"]
        self.check_value = self.options["value"]

        # Process namespace tokens
        managed = self.options.get("managed") or False
        namespace = self.project_config.project__package__namespace
        namespace_prefix = ""
        if managed:
            namespace_prefix = namespace + "__"

        self.object_name = self.object_name.replace("%%%NAMESPACE%%%", namespace_prefix)
        self.field_name = self.field_name.replace("%%%NAMESPACE%%%", namespace_prefix)

        self._poll()  # will block until poll_complete

        self.logger.info("Value Matched.")

        return True

    def _poll_action(self):
        query_results = self.sf.query(self._object_query)

        self.record = query_results["records"][0]

        self.poll_complete = not self._poll_again()

    def _poll_again(self):
        return not self.success

    @property
    def success(self):
        self.field_value = self.record[self.field_name]

        if isinstance(self.field_value, (bool)):
            self.check_value = process_bool_arg(self.check_value)
            self.field_value = process_bool_arg(self.field_value)
        elif isinstance(self.field_value, (int, float)):
            self.check_value = float(self.check_value)
            self.field_value = float(self.field_value)
        elif isinstance(field_value, (str)):
            self.check_value = str(self.check_value).lower()
            self.field_value = str(self.field_value).lower()

        self.logger.info(
            "{0}: Looking for {1} and found {2}".format(
                self.field_name, self.check_value, self.field_value
            )
        )
        return self.field_value == self.check_value

    @property
    def _object_query(self):
        return "SELECT {0} FROM {1} LIMIT 1".format(self.field_name, self.object_name)
