import unittest

from mock import MagicMock
from mock import patch
import responses

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.apex.testrunner import RunApexTests

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
        self.project_config.set_keychain(keychain)
        self.org_config = OrgConfig({
            'id': 'foo/1',
            'instance_url': 'example.com',
            'access_token': 'abc123',
        }, 'test')
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
        url = (self.base_tooling_url + 'query/?q=%0ASELECT+Id%2CApexClassId%2CTestTimestamp%2C%0A+++++++Message%2CMethodName%2COutcome%2C%0A+++++++RunTime%2CStackTrace%2C%0A+++++++%28SELECT+%0A++++++++++Id%2CCallouts%2CAsyncCalls%2CDmlRows%2CEmail%2C%0A++++++++++LimitContext%2CLimitExceptions%2CMobilePush%2C%0A++++++++++QueryRows%2CSosl%2CCpu%2CDml%2CSoql+%0A++++++++FROM+ApexTestResults%29+%0AFROM+ApexTestResult+%0AWHERE+AsyncApexJobId%3D%27JOB_ID1234567%27%0A')

        expected_response = {
            'done': True,

            'records': [{
                "attributes": {
                    "type": "ApexTestResult",
                    "url": "/services/data/v40.0/tooling/sobjects/ApexTestResult/07M41000009gbT3EAI"
                },
                "ApexClass": {
                    "attributes": {
                        "type": "ApexClass",
                        "url": "/services/data/v40.0/tooling/sobjects/ApexClass/01p4100000Fu4Z0AAJ"
                    },
                    "Name": "EP_TaskDependency_TEST"
                },
                "ApexClassId": 1,
                "ApexLogId": 1,
                "TestTimestamp": "2017-07-18T20:36:04.000+0000",
                "Id": "07M41000009gbT3EAI",
                "Message": "Test Passed",
                "MethodName": "TestMethod",
                "Outcome": "Pass",
                "QueueItem": {
                    "attributes": {
                        "type": "ApexTestQueueItem",
                        "url": "/services/data/v40.0/tooling/sobjects/ApexTestQueueItem/70941000000q7VsAAI"
                    },
                    "Status": "Completed",
                    "ExtendedStatus": "(4/4)"
                },
                "RunTime": 1707,
                "StackTrace": "1. ParentFunction\n2. ChildFunction",
                "Status": 'Completed',
                'Name': 'TestClass_TEST',
                "ApexTestResults": {
                    "size": 1,
                    "totalSize": 1,
                    "done": True,
                    "queryLocator": None,
                    "entityTypeName": "ApexTestResultLimits",
                    "records": [{
                        "attributes": {
                            "type": "ApexTestResultLimits",
                            "url": "/services/data/v40.0/tooling/sobjects/ApexTestResultLimits/05n41000002Y7OQAA0"
                        },
                        "Id": "05n41000002Y7OQAA0",
                        "Callouts": 0,
                        "AsyncCalls": 0,
                        "DmlRows": 5,
                        "Email": 0,
                        "LimitContext": "SYNC",
                        "LimitExceptions": None,
                        "MobilePush": 0,
                        "QueryRows": 20,
                        "Sosl": 0,
                        "Cpu": 471,
                        "Dml": 4,
                        "Soql": 5
                    }]
                }
            }]}

        responses.add(responses.GET, url,
                      match_querystring=True, json=expected_response)

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
