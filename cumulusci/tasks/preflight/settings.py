from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.utils import process_bool_arg

from simple_salesforce.exceptions import SalesforceMalformedRequest


class CheckSettingsValue(BaseSalesforceApiTask):
    task_options = {
        "settings_type": {
            "description": "The API name of the Settings entity to be checked, such as ChatterSettings.",
            "required": True,
        },
        "settings_field": {
            "description": "The API name of the field on the Settings entity to check.",
            "required": True,
        },
        "value": {"description": "The value to check for", "required": True},
    }

    def _run_task(self):
        try:
            results = self.tooling.query(
                f"SELECT {self.options['settings_field']} FROM {self.options['settings_type']}"
            )["records"]
        except SalesforceMalformedRequest:
            self.logger.error(
                "The specified settings entity or field could not be queried."
            )
            self.return_values = False
            return

        value = results[0].get(self.options["settings_field"])
        # Type-sensitive compare.
        if type(value) is bool:
            comparand = process_bool_arg(self.options["value"])
        elif type(value) is float:
            comparand = float(self.options["value"])
        elif type(value) is int:
            comparand = int(self.options["value"])
        else:
            comparand = self.options["value"]

        self.return_values = value == comparand

        self.logger.info(
            "Completed Settings preflight check with result {}".format(
                self.return_values
            )
        )
