import unittest

from mock import MagicMock
from mock import patch
import responses

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.salesforce import BaseSalesforceToolingApiTask
from cumulusci.tasks.salesforce import RunApexTests
from cumulusci.tasks.salesforce import RunApexTestsDebug


@patch('cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials',
    MagicMock(return_value=None))
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


@patch('cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials',
    MagicMock(return_value=None))
class TestRunApexTests(unittest.TestCase):

    def setUp(self):
        self.api_version = 38.0
        self.global_config = BaseGlobalConfig(
            {'project': {'api_version': self.api_version}})
        self.task_config = TaskConfig()
        self.task_config.config['options'] = {
            'junit_output': 'results_junit.xml',
            'poll_interval': 1,
            'test_name_match': '%_TEST',
        }
        self.project_config = BaseProjectConfig(self.global_config)
        self.project_config.config['project'] = {'package': {
            'api_version': self.api_version}}
        keychain = BaseProjectKeychain(self.project_config, '')
        app_config = ConnectedAppOAuthConfig()
        keychain.set_connected_app(app_config)
        self.project_config.set_keychain(keychain)
        self.org_config = OrgConfig({
            'id': 'foo/1',
            'instance_url': 'example.com',
            'access_token': 'abc123',
        })
        self.base_tooling_url = 'https://{}/services/data/v{}/tooling/'.format(
            self.org_config.instance_url, self.api_version)

    def _mock_apex_class_query(self):
        url = (self.base_tooling_url + 'query/?q=SELECT+Id%2C+Name+' +
            'FROM+ApexClass+WHERE+NamespacePrefix+%3D+null' +
            '+AND+%28Name+LIKE+%27%25_TEST%27%29')
        expected_response = {
            'done': True,
            'records': [{'Id': 1, 'Name': 'TestClass_TEST'}],
            'totalSize': 1,
        }
        responses.add(responses.GET, url, match_querystring=True,
            json=expected_response)

    def _mock_get_test_results(self):
        url = (self.base_tooling_url + 'query/?q=SELECT+StackTrace%2C+' +
            'Message%2C+ApexLogId%2C+AsyncApexJobId%2C+MethodName%2C+' +
            'Outcome%2C+ApexClassId%2C+TestTimestamp+FROM+ApexTestResult+' +
            'WHERE+AsyncApexJobId+%3D+%27JOB_ID1234567%27')
        expected_response = {
            'done': True,
            'records': [{
                'ApexClassId': 1,
                'ApexLogId': 1,
                'Id': 1,
                'Message': 'Test passed',
                'MethodName': 'TestMethod',
                'Name': 'TestClass_TEST',
                'Outcome': 'Pass',
                'StackTrace': '1. ParentFunction\n2. ChildFunction',
                'Status': 'Completed',
            }],
        }
        responses.add(responses.GET, url, match_querystring=True,
            json=expected_response)

    def _mock_tests_complete(self):
        url = (self.base_tooling_url + 'query/?q=SELECT+Id%2C+Status%2C+' +
            'ApexClassId+FROM+ApexTestQueueItem+WHERE+ParentJobId+%3D+%27' +
            'JOB_ID1234567%27')
        expected_response = {
            'done': True,
            'records': [{'Status': 'Completed'}],
        }
        responses.add(responses.GET, url, match_querystring=True,
            json=expected_response)

    def _mock_run_tests(self):
        url = self.base_tooling_url + 'runTestsAsynchronous'
        expected_response = 'JOB_ID1234567'
        responses.add(responses.POST, url, json=expected_response)

    @responses.activate
    def test_run_task(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_tests_complete()
        self._mock_get_test_results()
        task = RunApexTests(
            self.project_config, self.task_config, self.org_config)
        task()
        self.assertEqual(len(responses.calls), 4)


@patch('cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials',
    MagicMock(return_value=None))
class TestRunApexTestsDebug(TestRunApexTests):

    def setUp(self):
        super(TestRunApexTestsDebug, self).setUp()
        self.task_config.config['json_output'] = 'results.json'

    def _mock_create_debug_level(self):
        url = self.base_tooling_url + 'sobjects/DebugLevel/'
        expected_response = {
            'id': 1,
        }
        responses.add(responses.POST, url, json=expected_response)

    def _mock_create_trace_flag(self):
        url = self.base_tooling_url + 'sobjects/TraceFlag/'
        expected_response = {
            'id': 1,
        }
        responses.add(responses.POST, url, json=expected_response)

    def _mock_delete_debug_levels(self):
        url = self.base_tooling_url + 'sobjects/DebugLevel/1'
        responses.add(responses.DELETE, url)

    def _mock_delete_trace_flags(self):
        url = self.base_tooling_url + 'sobjects/TraceFlag/1'
        responses.add(responses.DELETE, url)

    def _mock_get_duration(self):
        url = (self.base_tooling_url + 'query/?q=SELECT+Id%2C+' +
            'Application%2C+DurationMilliseconds%2C+Location%2C+LogLength%2C' +
            '+LogUserId%2C+Operation%2C+Request%2C+StartTime%2C+Status+' +
            'from+ApexLog+where+Id+in+%28%271%27%29')
        expected_response = {
            'done': True,
            'records': [{'Id': 1, 'DurationMilliseconds': 1}],
            'totalSize': 1,
        }
        responses.add(responses.GET, url, match_querystring=True,
            json=expected_response)

    def _mock_get_log_body(self):
        url = self.base_tooling_url + 'sobjects/ApexLog/1/Body'
        expected_response = {
            'foo': 'bar',
        }
        responses.add(responses.GET, url, json=expected_response)

    def _mock_get_trace_flags(self):
        url = self.base_tooling_url + 'query/?q=Select+Id+from+TraceFlag+Where+TracedEntityId+%3D+%271%27'
        expected_response = {
            'records': [{'Id': 1}],
            'totalSize': 1,
        }
        responses.add(responses.GET, url, match_querystring=True,
            json=expected_response)

    def _mock_get_debug_levels(self):
        url = self.base_tooling_url + 'query/?q=Select+Id+from+DebugLevel'
        expected_response = {
            'records': [{'Id': 1}],
            'totalSize': 1,
        }
        responses.add(responses.GET, url, match_querystring=True,
            json=expected_response)

    @responses.activate
    def test_run_task(self):
        self._mock_apex_class_query()
        self._mock_get_trace_flags()
        self._mock_get_debug_levels()
        self._mock_delete_debug_levels()
        self._mock_delete_trace_flags()
        self._mock_create_debug_level()
        self._mock_create_trace_flag()
        self._mock_run_tests()
        self._mock_tests_complete()
        self._mock_get_test_results()
        self._mock_get_duration()
        self._mock_get_log_body()
        task = RunApexTestsDebug(
            self.project_config, self.task_config, self.org_config)
        task()
        self.assertEqual(len(responses.calls), 13)
