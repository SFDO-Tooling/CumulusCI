from cumulusci.salesforce_api.metadata import ApiRetrieveInstalledPackages
from cumulusci.tasks.salesforce import BaseSalesforceMetadataApiTask


class GetInstalledPackages(BaseSalesforceMetadataApiTask):
    api_class = ApiRetrieveInstalledPackages
    name = 'GetInstalledPackages'
