from cumulusci.salesforce_api.metadata import ApiListMetadataTypes
from cumulusci.tasks.salesforce import BaseRetrieveMetadata


class DescribeMetadataTypes(BaseRetrieveMetadata):
    api_class = ApiListMetadataTypes
    task_options = {
        "api_version": {
            "description": "Override the API version used to list metadatatypes"
        },
    }

    def _init_options(self, kwargs):
        super(DescribeMetadataTypes, self)._init_options(kwargs)
        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

    def _get_api(self):
        return self.api_class(self, self.options.get("api_version"))

    def _run_task(self):
        api_object = self._get_api()
        self.return_values = api_object()
        return self.return_values
