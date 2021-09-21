from cumulusci.salesforce_api.metadata import ApiNewProfile
from cumulusci.tasks.salesforce.BaseSalesforceMetadataApiTask import (
    BaseSalesforceMetadataApiTask,
)


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

    def _get_api(self):

        return self.api_class(
            self,
            license_id=self.options.get("test_level"),
            name=self.name,
            description=self.description,
        )

    # def _run_task(self):
    #
