from cumulusci.tasks.salesforce import BaseSalesforceTask


class BaseSalesforceMetadataApiTask(BaseSalesforceTask):
    api_class = None
    name = "BaseSalesforceMetadataApiTask"

    def _get_api(self):
        return self.api_class(self)

    def _run_task(self):
        api = self._get_api()
        result = None
        if api:
            result = api()
            self.org_config.reset_installed_packages()
            self.return_values = result
        return result
