from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.tasks import BaseSalesforceTask
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask


class CheckMyDomainActive(BaseSalesforceTask):
    def _run_task(self):
        self.return_values = (
            ".my." in self.org_config.instance_url
            or ".cloudforce.com" in self.org_config.instance_url
        )

        self.logger.info(
            f"Completed My Domain preflight check with result {self.return_values}"
        )


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
        "treat_missing_as_failure": {
            "description": "If True, treat a missing Settings entity as a preflight failure, instead of raising an exception. Defaults to False.",
            "required": False,
        },
    }

    def _run_task(self):
        field = self.options["settings_field"]
        entity = self.options["settings_type"]
        try:
            results = self.tooling.query(f"SELECT {field} FROM {entity}")["records"]
        except SalesforceMalformedRequest as e:
            self.logger.error(
                f"The settings value {entity}.{field} could not be queried: {e}"
            )
            self.return_values = False

            if not process_bool_arg(
                self.options.get("treat_missing_as_failure", False)
            ):
                raise e

            return

        if not results:
            self.logger.info(
                "Located no Settings records. Returning negative preflight result."
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
            f"Completed Settings preflight check with result {self.return_values}"
        )
