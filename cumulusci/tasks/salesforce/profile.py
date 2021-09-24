from cumulusci.salesforce_api.metadata import ApiNewProfile
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import (
    BaseSalesforceMetadataApiTask,
)

# TODO: Minimum api versionm for this task?


class ProfileSoap(BaseSalesforceMetadataApiTask):
    api_class = ApiNewProfile
    task_options = {
        "license": {
            "description": "The name of the salesforce license to use in the profile, defaults to 'Salesforce'",
            "required": True,
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
        super(ProfileSoap, self)._init_options(kwargs)

        self.license = self.options.get("license", "Salesforce")
        self.name = self.options.get("name", None)
        self.description = self.options.get("description", "")

    def _get_user_license_id(self, license_name):
        """Returns the Id of a UserLicense from a given Name"""
        self.sf = get_simple_salesforce_connection(
            self.project_config,
            self.org_config,
            api_version=None,
            base_url=None,
        )
        res = self.sf.query_all(
            f"SELECT Id, Name FROM UserLicense WHERE Name = '{license_name}'"
        )
        return res["records"][0]["Id"]

    def _get_api(self):
        return self.api_class(
            self,
            license_id=self._get_user_license_id(self.license),
            name=self.name,
            description=self.description,
        )

    def _run_task(self):
        api = self._get_api()
        result = None
        if api:
            result = api()
            self.org_config.reset_installed_packages()
            self.return_values = result
            self.logger.info(f"Profile '{self.name}' created with id: {result}")
        return result
