from salesforce_bulk import SalesforceBulk

from cumulusci.core.exceptions import ConfigError
from cumulusci.core.tasks import BaseSalesforceTask
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection


class BaseSalesforceApiTask(BaseSalesforceTask):
    name = "BaseSalesforceApiTask"
    api_version = None

    def _init_task(self):
        super()._init_task()
        self.sf = self._init_api()
        self.bulk = self._init_bulk()
        self.tooling = self._init_api("tooling")
        self._init_class()

    def _init_api(self, base_url=None):
        rv = get_simple_salesforce_connection(
            self.project_config,
            self.org_config,
            api_version=self.api_version,
            base_url=base_url,
        )

        return rv

    def _init_bulk(self):
        version = self.api_version or self.project_config.project__package__api_version
        if not version:
            raise ConfigError("Cannot find Salesforce version")
        return SalesforceBulk(
            host=self.org_config.instance_url.replace("https://", "").rstrip("/"),
            sessionId=self.org_config.access_token,
            API_version=version,
        )

    def _init_class(self):
        pass

    def _get_tooling_object(self, obj_name):
        obj = getattr(self.tooling, obj_name)
        obj.base_url = obj.base_url.replace("/sobjects/", "/tooling/sobjects/")
        return obj
