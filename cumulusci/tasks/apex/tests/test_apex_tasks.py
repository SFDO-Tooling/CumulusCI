from future import standard_library

standard_library.install_aliases()
import http.client
import os
import shutil
import tempfile
import unittest

import responses
from mock import MagicMock, patch
from simple_salesforce import SalesforceGeneralError

from cumulusci.core.config import (
    BaseGlobalConfig,
    BaseProjectConfig,
    OrgConfig,
    TaskConfig,
)
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.exceptions import (
    ApexCompilationException,
    ApexException,
    ApexTestException,
    SalesforceException,
    TaskOptionsError,
)
from cumulusci.tasks.apex.anon import AnonymousApexTask
from cumulusci.tasks.apex.batch import BatchApexWait
from cumulusci.tasks.apex.testrunner import RunApexTests
from cumulusci.utils import temporary_dir


@patch(
    "cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials",
    MagicMock(return_value=None),
)
class TestRunApexTests(unittest.TestCase):
    def setUp(self):
        self.api_version = 38.0
        self.global_config = BaseGlobalConfig(
            {"project": {"api_version": self.api_version}}
        )
        self.task_config = TaskConfig()
        self.task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
        }
        self.project_config = BaseProjectConfig(
            self.global_config, config={"noyaml": True}
        )
        self.project_config.config["project"] = {
            "package": {"api_version": self.api_version}
        }
        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)
        self.org_config = OrgConfig(
            {"id": "foo/1", "instance_url": "example.com", "access_token": "abc123"},
            "test",
        )
        self.base_tooling_url = "https://{}/services/data/v{}/tooling/".format(
            self.org_config.instance_url, self.api_version
        )

    def _mock_apex_class_query(self):
        url = (
            self.base_tooling_url
            + "query/?q=SELECT+Id%2C+Name+"
            + "FROM+ApexClass+WHERE+NamespacePrefix+%3D+null"
            + "+AND+%28Name+LIKE+%27%25_TEST%27%29"
        )
        expected_response = {
            "done": True,
            "records": [{"Id": 1, "Name": "TestClass_TEST"}],
            "totalSize": 1,
        }
        responses.add(
            responses.GET, url, match_querystring=True, json=expected_response
        )

    def _mock_get_test_results(self, outcome="Pass"):
        url = (
            self.base_tooling_url
            + "query/?q=%0ASELECT+Id%2CApexClassId%2CTestTimestamp%2C%0A+++++++Message%2CMethodName%2COutcome%2C%0A+++++++RunTime%2CStackTrace%2C%0A+++++++%28SELECT+%0A++++++++++Id%2CCallouts%2CAsyncCalls%2CDmlRows%2CEmail%2C%0A++++++++++LimitContext%2CLimitExceptions%2CMobilePush%2C%0A++++++++++QueryRows%2CSosl%2CCpu%2CDml%2CSoql+%0A++++++++FROM+ApexTestResults%29+%0AFROM+ApexTestResult+%0AWHERE+AsyncApexJobId%3D%27JOB_ID1234567%27%0A"
        )

        expected_response = {
            "done": True,
            "records": [
                {
                    "attributes": {
                        "type": "ApexTestResult",
                        "url": "/services/data/v40.0/tooling/sobjects/ApexTestResult/07M41000009gbT3EAI",
                    },
                    "ApexClass": {
                        "attributes": {
                            "type": "ApexClass",
                            "url": "/services/data/v40.0/tooling/sobjects/ApexClass/01p4100000Fu4Z0AAJ",
                        },
                        "Name": "EP_TaskDependency_TEST",
                    },
                    "ApexClassId": 1,
                    "ApexLogId": 1,
                    "TestTimestamp": "2017-07-18T20:36:04.000+0000",
                    "Id": "07M41000009gbT3EAI",
                    "Message": "Test Passed",
                    "MethodName": "TestMethod",
                    "Outcome": outcome,
                    "QueueItem": {
                        "attributes": {
                            "type": "ApexTestQueueItem",
                            "url": "/services/data/v40.0/tooling/sobjects/ApexTestQueueItem/70941000000q7VsAAI",
                        },
                        "Status": "Completed",
                        "ExtendedStatus": "(4/4)",
                    },
                    "RunTime": 1707,
                    "StackTrace": "1. ParentFunction\n2. ChildFunction",
                    "Status": "Completed",
                    "Name": "TestClass_TEST",
                    "ApexTestResults": {
                        "size": 1,
                        "totalSize": 1,
                        "done": True,
                        "queryLocator": None,
                        "entityTypeName": "ApexTestResultLimits",
                        "records": [
                            {
                                "attributes": {
                                    "type": "ApexTestResultLimits",
                                    "url": "/services/data/v40.0/tooling/sobjects/ApexTestResultLimits/05n41000002Y7OQAA0",
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
                                "Soql": 5,
                            }
                        ],
                    },
                }
            ],
        }

        responses.add(
            responses.GET, url, match_querystring=True, json=expected_response
        )

    def _mock_tests_complete(self):
        url = (
            self.base_tooling_url
            + "query/?q=SELECT+Id%2C+Status%2C+"
            + "ApexClassId+FROM+ApexTestQueueItem+WHERE+ParentJobId+%3D+%27"
            + "JOB_ID1234567%27"
        )
        expected_response = {"done": True, "records": [{"Status": "Completed"}]}
        responses.add(
            responses.GET, url, match_querystring=True, json=expected_response
        )

    def _mock_run_tests(self, success=True):
        url = self.base_tooling_url + "runTestsAsynchronous"
        if success:
            expected_response = "JOB_ID1234567"
            responses.add(responses.POST, url, json=expected_response)
        else:
            responses.add(responses.POST, url, status=http.client.SERVICE_UNAVAILABLE)

    @responses.activate
    def test_run_task(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_tests_complete()
        self._mock_get_test_results()
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        task()
        self.assertEqual(len(responses.calls), 4)

    @responses.activate
    def test_run_task__server_error(self):
        self._mock_apex_class_query()
        self._mock_run_tests(success=False)
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        with self.assertRaises(SalesforceGeneralError):
            task()

    @responses.activate
    def test_run_task__failed(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_tests_complete()
        self._mock_get_test_results("Fail")
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        with self.assertRaises(ApexTestException):
            task()

    def test_get_namespace_filter__managed(self):
        task_config = TaskConfig({"options": {"managed": True, "namespace": "testns"}})
        task = RunApexTests(self.project_config, task_config, self.org_config)
        namespace = task._get_namespace_filter()
        self.assertEqual("'testns'", namespace)

    def test_get_namespace_filter__managed_no_namespace(self):
        task_config = TaskConfig({"options": {"managed": True}})
        task = RunApexTests(self.project_config, task_config, self.org_config)
        with self.assertRaises(TaskOptionsError):
            namespace = task._get_namespace_filter()

    def test_get_test_class_query__exclude(self):
        task_config = TaskConfig(
            {"options": {"test_name_match": "%_TEST", "test_name_exclude": "EXCL"}}
        )
        task = RunApexTests(self.project_config, task_config, self.org_config)
        query = task._get_test_class_query()
        self.assertEqual(
            "SELECT Id, Name FROM ApexClass WHERE NamespacePrefix = null "
            "AND (Name LIKE '%_TEST') AND (NOT Name LIKE 'EXCL')",
            query,
        )

    def test_run_task__no_tests(self):
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        task._get_test_classes = MagicMock(return_value={"totalSize": 0})
        task()
        self.assertIsNone(task.result)


@patch(
    "cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials",
    MagicMock(return_value=None),
)
class TestAnonymousApexTask(unittest.TestCase):
    def setUp(self):
        self.api_version = 42.0
        self.global_config = BaseGlobalConfig(
            {"project": {"api_version": self.api_version}}
        )
        self.tmpdir = tempfile.mkdtemp(dir=".")
        apex_path = os.path.join(self.tmpdir, "test.apex")
        with open(apex_path, "w") as f:
            f.write('System.debug("from file")')
        self.task_config = TaskConfig()
        self.task_config.config["options"] = {
            "path": apex_path,
            "apex": 'system.debug("Hello World!")',
            "namespaced": True,
        }
        self.project_config = BaseProjectConfig(
            self.global_config, config={"noyaml": True}
        )
        self.project_config.config = {
            "project": {
                "package": {"namespace": "abc", "api_version": self.api_version}
            }
        }
        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)
        self.org_config = OrgConfig(
            {"id": "foo/1", "instance_url": "example.com", "access_token": "abc123"},
            "test",
        )
        self.base_tooling_url = "https://{}/services/data/v{}/tooling/".format(
            self.org_config.instance_url, self.api_version
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _get_url_and_task(self):
        task = AnonymousApexTask(self.project_config, self.task_config, self.org_config)
        url = task.tooling.base_url + "executeAnonymous"
        return task, url

    def test_validate_options(self):
        task_config = TaskConfig({})
        with self.assertRaises(TaskOptionsError):
            AnonymousApexTask(self.project_config, task_config, self.org_config)

    def test_run_from_path_outside_repo(self):
        task_config = TaskConfig({"options": {"path": "/"}})
        task = AnonymousApexTask(self.project_config, task_config, self.org_config)
        with self.assertRaises(TaskOptionsError):
            task()

    def test_run_path_not_found(self):
        task_config = TaskConfig({"options": {"path": "bogus"}})
        task = AnonymousApexTask(self.project_config, task_config, self.org_config)
        with self.assertRaises(TaskOptionsError):
            task()

    def test_prepare_apex(self):
        task = AnonymousApexTask(self.project_config, self.task_config, self.org_config)
        before = "String %%%NAMESPACE%%%str = 'foo';"
        expected = "String abc__str = 'foo';"
        self.assertEqual(expected, task._prepare_apex(before))

    @responses.activate
    def test_run_anonymous_apex_success(self):
        task, url = self._get_url_and_task()
        resp = {"compiled": True, "success": True}
        responses.add(responses.GET, url, status=200, json=resp)
        task()

    @responses.activate
    def test_run_string_only(self):
        task_config = TaskConfig({"options": {"apex": 'System.debug("test");'}})
        task = AnonymousApexTask(self.project_config, task_config, self.org_config)
        url = task.tooling.base_url + "executeAnonymous"
        responses.add(
            responses.GET, url, status=200, json={"compiled": True, "success": True}
        )
        task()

    @responses.activate
    def test_run_anonymous_apex_status_fail(self):
        task, url = self._get_url_and_task()
        responses.add(responses.GET, url, status=418, body="I'm a teapot")
        with self.assertRaises(SalesforceGeneralError) as cm:
            task()
        err = cm.exception
        self.assertEqual(str(err), "Error Code 418. Response content: I'm a teapot")
        self.assertTrue(err.url.startswith(url))
        self.assertEqual(err.status, 418)
        self.assertEqual(err.content, "I'm a teapot")

    @responses.activate
    def test_run_anonymous_apex_compile_except(self):
        task, url = self._get_url_and_task()
        problem = "Unexpected token '('."
        resp = {
            "compiled": False,
            "compileProblem": problem,
            "success": False,
            "line": 1,
            "column": 13,
            "exceptionMessage": "",
            "exceptionStackTrace": "",
            "logs": "",
        }
        responses.add(responses.GET, url, status=200, json=resp)
        with self.assertRaises(ApexCompilationException) as cm:
            task()
        err = cm.exception
        self.assertEqual(err.args[0], 1)
        self.assertEqual(err.args[1], problem)

    @responses.activate
    def test_run_anonymous_apex_except(self):
        task, url = self._get_url_and_task()
        problem = "Unexpected token '('."
        trace = "Line 0, Column 99"
        resp = {
            "compiled": True,
            "compileProblem": "",
            "success": False,
            "line": 1,
            "column": 13,
            "exceptionMessage": problem,
            "exceptionStackTrace": trace,
            "logs": "",
        }
        responses.add(responses.GET, url, status=200, json=resp)
        with self.assertRaises(ApexException) as cm:
            task()
        err = cm.exception
        self.assertEqual(err.args[0], problem)
        self.assertEqual(err.args[1], trace)


@patch(
    "cumulusci.tasks.salesforce.BaseSalesforceTask._update_credentials",
    MagicMock(return_value=None),
)
class TestRunBatchApex(unittest.TestCase):
    def setUp(self):
        self.api_version = 42.0
        self.global_config = BaseGlobalConfig(
            {"project": {"api_version": self.api_version}}
        )
        self.task_config = TaskConfig()
        self.task_config.config["options"] = {
            "class_name": "ADDR_Seasonal_BATCH",
            "poll_interval": 1,
        }
        self.project_config = BaseProjectConfig(
            self.global_config, config={"noyaml": True}
        )
        self.project_config.config["project"] = {
            "package": {"api_version": self.api_version}
        }
        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)
        self.org_config = OrgConfig(
            {"id": "foo/1", "instance_url": "example.com", "access_token": "abc123"},
            "test",
        )
        self.base_tooling_url = "https://{}/services/data/v{}/tooling/".format(
            self.org_config.instance_url, self.api_version
        )

    def _get_query_resp(self):
        return {
            "size": 1,
            "totalSize": 1,
            "done": True,
            "queryLocator": None,
            "entityTypeName": "AsyncApexJob",
            "records": [
                {
                    "attributes": {
                        "type": "AsyncApexJob",
                        "url": "/services/data/v43.0/tooling/sobjects/AsyncApexJob/707L0000014nnPHIAY",
                    },
                    "Id": "707L0000014nnPHIAY",
                    "ApexClass": {
                        "attributes": {
                            "type": "ApexClass",
                            "url": "/services/data/v43.0/tooling/sobjects/ApexClass/01pL000000109ndIAA",
                        },
                        "Name": "ADDR_Seasonal_BATCH",
                    },
                    "Status": "Completed",
                    "ExtendedStatus": None,
                    "TotalJobItems": 1,
                    "JobItemsProcessed": 1,
                    "NumberOfErrors": 0,
                    "CreatedDate": "2018-08-07T16:00:56.000+0000",
                    "CompletedDate": "2018-08-07T16:01:57.000+0000",
                }
            ],
        }

    def _get_url_and_task(self):
        task = BatchApexWait(self.project_config, self.task_config, self.org_config)
        url = (
            task.tooling.base_url
            + "query/?q=SELECT+Id%2C+ApexClass.Name%2C+Status%2C+ExtendedStatus%2C+TotalJobItems%2C+JobItemsProcessed%2C+NumberOfErrors%2C+CreatedDate%2C+CompletedDate+FROM+AsyncApexJob+WHERE+JobType%3D%27BatchApex%27+AND+ApexClass.Name%3D%27ADDR_Seasonal_BATCH%27+ORDER+BY+CreatedDate+DESC+LIMIT+1"
        )
        return task, url

    @responses.activate
    def test_run_batch_apex_status_fail(self):
        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"][0]["NumberOfErrors"] = 1
        response["records"][0]["ExtendedStatus"] = "Bad Status"
        responses.add(responses.GET, url, json=response)
        with self.assertRaises(SalesforceException) as cm:
            task()
        err = cm.exception
        self.assertEqual(err.args[0], "Bad Status")

    @responses.activate
    def test_run_batch_apex_status_ok(self):
        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        responses.add(responses.GET, url, json=response)
        task()

    @responses.activate
    def test_run_batch_apex_calc_delta(self):
        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        responses.add(responses.GET, url, json=response)
        task()
        self.assertEqual(task.delta, 61)
