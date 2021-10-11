from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.metadata import ApiNewProfile
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import (
    BaseSalesforceMetadataApiTask,
)


class CreateBlankProfile(BaseSalesforceMetadataApiTask):
    api_class = ApiNewProfile
    task_options = {
        "license": {
            "description": "The name of the salesforce license to use in the profile, defaults to 'Salesforce'",
        },
        "license_id": {
            "description": "The ID of the salesforce license to use in the profile.",
        },
        "name": {
            "description": "The name of the the new profile",
            "required": True,
        },
        "description": {
            "description": "The description of the the new profile",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super(CreateBlankProfile, self)._init_options(kwargs)
        if {"license", "license_id"}.isdisjoint(self.options.keys()):
            raise TaskOptionsError(
                "Either the name or the ID of the user license must be set."
            )
        self.license = self.options.get("license", "Salesforce")

    def _run_task(self):

        self.name = self.options["name"]
        self.description = self.options.get("description") or ""
        self.license_id = self.options.get("license_id")

        if not self.license_id:
            self.license_id = self._get_user_license_id(self.license)

        api = self._get_api()
        result = api()
        self.return_values = {"profile_id": result}
        self.logger.info(f"Profile '{self.name}' created with id: {result}")
        return result

    def _get_user_license_id(self, license_name):
        """Returns the Id of a UserLicense from a given Name"""
        self.sf = get_simple_salesforce_connection(
            self.project_config,
            self.org_config,
            api_version=self.org_config.latest_api_version,
            base_url=None,
        )
        res = self.sf.query(
            f"SELECT Id, Name FROM UserLicense WHERE Name = '{license_name}' LIMIT 1"
        )
        if res["records"]:
            return res["records"][0]["Id"]
        else:
            raise TaskOptionsError(f"License name '{license_name}' was not found.")

    def _get_api(self):
        return self.api_class(
            self,
            api_version=self.org_config.latest_api_version,
            license_id=self.license_id,
            name=self.name,
            description=self.description,
        )
