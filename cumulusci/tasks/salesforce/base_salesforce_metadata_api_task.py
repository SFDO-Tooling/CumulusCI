from cumulusci.tasks.salesforce import BaseSalesforceTask
from cumulusci.salesforce_api.metadata import BaseMetadataApiCall
from typing import Type


class BaseSalesforceMetadataApiTask(BaseSalesforceTask):
    api_class: Type[BaseMetadataApiCall] = BaseMetadataApiCall
    name = "BaseSalesforceMetadataApiTask"

    def _get_api(self):
        return self.api_class(self)

    def _run_task(self):
        api = self._get_api()
        result = None
        if api:
            result = api()
            self.return_values = result
        return result
