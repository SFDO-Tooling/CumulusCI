from typing import Any
from cumulusci.salesforce_api.metadata import ApiListMetadataTypes

from cumulusci.tasks.salesforce import BaseRetrieveMetadata
from defusedxml.minidom import parseString

class RetrieveMetadataTypes(BaseRetrieveMetadata):
    api_2= ApiListMetadataTypes
    task_options = {
        "api_version": {
            "description": "Override the API version used to list metadata"
        },
        
    }

    def _run_task(self):

        api_object = self.api_2(self, "58.0" )
        root = api_object._get_response().content.decode("utf-8")

        self.logger.info(api_object._process_response(root))
        
       
        

        