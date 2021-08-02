from pprint import pformat

from cumulusci.salesforce_api.metadata import ApiRetrieveInstalledPackages
from cumulusci.tasks.salesforce import BaseSalesforceMetadataApiTask


class GetInstalledPackages(BaseSalesforceMetadataApiTask):
    api_class = ApiRetrieveInstalledPackages
    name = "GetInstalledPackages"

    def _run_task(self):
        result = super()._run_task()

        self.logger.info(f"{self.__class__.name} returned\n {pformat(result)}")
