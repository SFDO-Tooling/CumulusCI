import unittest

import responses

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.tasks.salesforce import BaseSalesforceToolingApiTask


class TestBaseSalesforceToolingApiTask(unittest.TestCase):

    def setUp(self):
        self.api_version = 38.0
        self.global_config = BaseGlobalConfig(
            {'project': {'api_version': self.api_version}})
        self.project_config = BaseProjectConfig(self.global_config)
        self.project_config.config['project'] = {
            'api_version': self.api_version}
        self.task_config = TaskConfig()
        self.org_config = OrgConfig({
            'instance_url': 'foo',
            'access_token': 'bar',
        })

    def test_get_tooling_object(self):
        task = BaseSalesforceToolingApiTask(
            self.project_config, self.task_config, self.org_config)
        obj = task._get_tooling_object('TestObject')
        self.assertEqual(obj.base_url, 'https://foo/services/data/v' +
            '{}/tooling/sobjects/TestObject/'.format(self.api_version))
