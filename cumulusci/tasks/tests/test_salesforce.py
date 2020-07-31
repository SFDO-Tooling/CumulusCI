import unittest

from unittest.mock import MagicMock
from unittest.mock import patch

from cumulusci.core.config import UniversalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


@patch(
    "cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials",
    MagicMock(return_value=None),
)
class TestSalesforceToolingTask(unittest.TestCase):
    def setUp(self):
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
        self.assertEqual(obj.base_url, url)

    def test_default_client_name(self):
        task = BaseSalesforceApiTask(
            self.project_config, self.task_config, self.org_config
        )
        task._init_task()
        self.assertIn("Sforce-Call-Options", task.sf.headers)
        self.assertIn("CumulusCI/", task.sf.headers["Sforce-Call-Options"])

    def test_connected_app_client_name(self):
        self.project_config.keychain.set_service(
            "connectedapp", ServiceConfig({"client_id": "test123"})
        )

        task = BaseSalesforceApiTask(
            self.project_config, self.task_config, self.org_config
        )
        task._init_task()
        self.assertIn("Sforce-Call-Options", task.sf.headers)
        self.assertNotIn("CumulusCI/", task.sf.headers["Sforce-Call-Options"])
        self.assertIn("test123", task.sf.headers["Sforce-Call-Options"])
