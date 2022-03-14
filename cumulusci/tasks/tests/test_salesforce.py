from unittest.mock import MagicMock, patch

from cumulusci.core.config import (
    BaseProjectConfig,
    OrgConfig,
    ServiceConfig,
    TaskConfig,
    UniversalConfig,
)
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


@patch(
    "cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials",
    MagicMock(return_value=None),
)
class TestSalesforceToolingTask:
    def setup_method(self):
        self.api_version = 36.0
        self.universal_config = UniversalConfig(
            {"project": {"package": {"api_version": self.api_version}}}
        )
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.project_config.config["project"] = {
            "package": {"api_version": self.api_version}
        }
        self.project_config.config["services"] = {
            "connectedapp": {"attributes": {"client_id": {}}}
        }
        self.keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(self.keychain)

        self.task_config = TaskConfig()
        self.org_config = OrgConfig(
            {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
        )
        self.base_tooling_url = "{}/services/data/v{}/tooling/".format(
            self.org_config.instance_url, self.api_version
        )

    def test_get_tooling_object(self):
        task = BaseSalesforceApiTask(
            self.project_config, self.task_config, self.org_config
        )
        task._init_task()
        obj = task._get_tooling_object("TestObject")
        url = self.base_tooling_url + "sobjects/TestObject/"
        assert obj.base_url == url

    def test_default_client_name(self):
        task = BaseSalesforceApiTask(
            self.project_config, self.task_config, self.org_config
        )
        task._init_task()
        assert "Sforce-Call-Options" in task.sf.headers
        assert "CumulusCI/" in task.sf.headers["Sforce-Call-Options"]

    def test_connected_app_client_name(self):
        self.project_config.keychain.set_service(
            "connectedapp", "test_alias", ServiceConfig({"client_id": "test123"})
        )

        task = BaseSalesforceApiTask(
            self.project_config, self.task_config, self.org_config
        )
        task._init_task()
        assert "Sforce-Call-Options" in task.sf.headers
        assert "CumulusCI/" not in task.sf.headers["Sforce-Call-Options"]
        assert "test123" in task.sf.headers["Sforce-Call-Options"]
