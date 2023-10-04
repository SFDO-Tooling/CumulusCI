from typing import Any
from cumulusci.salesforce_api.metadata import ApiListMetadataTypes

from cumulusci.tasks.salesforce import BaseRetrieveMetadata
from defusedxml.minidom import parseString

class RetrieveMetadataTypes(BaseRetrieveMetadata):
    api_class= ApiListMetadataTypes
    task_options = {
        "api_version": {
            "description": "Override the API version used to list metadatatypes"
        },
        
    }
    def _init_options(self, kwargs):
        super(RetrieveMetadataTypes, self)._init_options(kwargs)
        if "api_version" not in self.options:
            self.options[
                "api_version"
            ] = self.project_config.project__package__api_version

    def _get_api(self):
        return self.api_class(
            self, self.options.get("api_version")
        )

    def _run_task(self):
        api_object = self._get_api()
        root = api_object._get_response().content.decode("utf-8")
        self.logger.info(api_object._process_response(root))
        
       
        

        