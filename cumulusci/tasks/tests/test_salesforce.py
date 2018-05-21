import unittest

from mock import MagicMock
from mock import patch
import responses

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


@patch('cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials',
    MagicMock(return_value=None))
class TestSalesforceToolingTask(unittest.TestCase):

    def setUp(self):
        self.api_version = 36.0
        self.global_config = BaseGlobalConfig(
            {'project': {'package': {'api_version': self.api_version}}})
        self.project_config = BaseProjectConfig(self.global_config)
        self.project_config.config['project'] = {
            'package': {
                'api_version': self.api_version,
            }
        }
        self.task_config = TaskConfig()
        self.org_config = OrgConfig({
            'instance_url': 'example.com',
            'access_token': 'abc123',
        }, 'test')
        self.base_tooling_url = 'https://{}/services/data/v{}/tooling/'.format(
            self.org_config.instance_url, self.api_version)

    def test_get_tooling_object(self):
        task = BaseSalesforceApiTask(
            self.project_config, self.task_config, self.org_config)
        obj = task._get_tooling_object('TestObject')
        url = self.base_tooling_url + 'sobjects/TestObject/'
        self.assertEqual(obj.base_url, url)
