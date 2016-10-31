import unittest

from mock import patch
import responses

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.salesforce import BaseSalesforceToolingApiTask
from cumulusci.tasks.salesforce import RunApexTests

class TestBaseSalesforceToolingApiTask(unittest.TestCase):

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
        })
        self.base_tooling_url = 'https://{}/services/data/v{}/tooling/'.format(
            self.org_config.instance_url, self.api_version)

    def test_get_tooling_object(self):
        task = BaseSalesforceToolingApiTask(
            self.project_config, self.task_config, self.org_config)
        obj = task._get_tooling_object('TestObject')
        url = self.base_tooling_url + 'sobjects/TestObject/'
        self.assertEqual(obj.base_url, url)

class TestRunApexTests(unittest.TestCase):

    def setUp(self):
        self.api_version = 36.0
        self.global_config = BaseGlobalConfig(
            {'project': {'api_version': self.api_version}})
        self.task_config = TaskConfig()
        self.task_config.config['options'] = {
            'junit_output': 'test_junit_output.txt',
            'poll_interval': 1,
            'test_name_match': '%_TEST',
        }
        self.project_config = BaseProjectConfig(self.global_config)
        self.project_config.config['project'] = {'package': {
            'api_version': self.api_version}}
        keychain = BaseProjectKeychain(self.project_config, '')
        self.project_config.set_keychain(keychain)
        self.org_config = OrgConfig({
            'instance_url': 'example.com',
            'access_token': 'abc123',
        })
        self.base_tooling_url = 'https://{}/services/data/v{}/tooling/'.format(
            self.org_config.instance_url, self.api_version)

    def _mock_apex_class_query(self):
        url = self.base_tooling_url + 'query/'
        expected_response = {
            'done': True,
            'records': [{
                'ApexClassId': 1,
                'Id': 1,
                'Message': 'Test passed',
                'MethodName': 'TestMethod',
                'Name': 'TestClass_TEST',
                'Outcome': 'Pass',
                'StackTrace': '1. ParentFunction\n2. ChildFunction',
                'Status': 'Completed',
            }],
            'totalSize': 1,
        }
        responses.add(responses.GET, url, json=expected_response)

    def _mock_run_tests(self):
        url = self.base_tooling_url + 'runTestsAsynchronous'
        expected_response = {
            'foo': 'bar',
        }
        responses.add(responses.GET, url, json=expected_response)

    @responses.activate
    def test_run_task(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        task = RunApexTests(
            self.project_config, self.task_config, self.org_config)
        with patch.object(OrgConfig, 'refresh_oauth_token'):
            task()
