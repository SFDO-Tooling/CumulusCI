import http.client
import logging
import os
import shutil
import tempfile
from copy import deepcopy
from unittest.mock import MagicMock, Mock, patch

import pytest
import responses
from simple_salesforce import SalesforceGeneralError

from cumulusci.core import exceptions as exc
from cumulusci.core.config import (
    BaseProjectConfig,
    OrgConfig,
    TaskConfig,
    UniversalConfig,
)
from cumulusci.core.exceptions import (
    ApexCompilationException,
    ApexException,
    ApexTestException,
    CumulusCIException,
    SalesforceException,
    TaskOptionsError,
)
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.tasks.apex.anon import AnonymousApexTask
from cumulusci.tasks.apex.batch import BatchApexWait
from cumulusci.tasks.apex.testrunner import RunApexTests
from cumulusci.utils.version_strings import StrictVersion


@patch(
    "cumulusci.core.tasks.BaseSalesforceTask._update_credentials",
    MagicMock(return_value=None),
)
class TestRunApexTests(MockLoggerMixin):
    def setup_method(self):
        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages
        self.api_version = 38.0
        self.universal_config = UniversalConfig(
            {"project": {"api_version": self.api_version}}
        )
        self.task_config = TaskConfig()
        self.task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
        }
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.project_config.config["project"] = {
            "package": {"api_version": self.api_version}
        }
        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)
        self.org_config = OrgConfig(
            {
                "id": "foo/1",
                "instance_url": "https://example.com",
                "access_token": "abc123",
            },
            "test",
        )
        self.base_tooling_url = "{}/services/data/v{}/tooling/".format(
            self.org_config.instance_url, self.api_version
        )

    def _mock_apex_class_query(self, name="TestClass_TEST", namespace=None):
        namespace_param = "null" if namespace is None else f"%27{namespace}%27"
        url = (
            self.base_tooling_url
            + "query/?q=SELECT+Id%2C+Name+"
            + f"FROM+ApexClass+WHERE+NamespacePrefix+%3D+{namespace_param}"
            + "+AND+%28Name+LIKE+%27%25_TEST%27%29"
        )
        expected_response = {
            "done": True,
            "records": [{"Id": 1, "Name": name}],
            "totalSize": 1,
        }
        responses.add(
            responses.GET, url, match_querystring=True, json=expected_response
        )

    def _get_mock_test_query_results(self, methodnames, outcomes, messages):
        record_base = {
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
            "Message": None,
            "MethodName": None,
            "Outcome": None,
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

        return_value = {"done": True, "records": []}

        for (method_name, outcome, message) in zip(methodnames, outcomes, messages):
            this_result = deepcopy(record_base)
            this_result["Message"] = message
            this_result["Outcome"] = outcome
            this_result["MethodName"] = method_name
            return_value["records"].append(this_result)

        return return_value

    def _get_mock_test_query_url(self, job_id):
        return (
            self.base_tooling_url
            + "query/?q=%0ASELECT+Id%2CApexClassId%2CTestTimestamp%2C%0A+++++++Message%2CMethodName%2COutcome%2C%0A+++++++RunTime%2CStackTrace%2C%0A+++++++%28SELECT%0A++++++++++Id%2CCallouts%2CAsyncCalls%2CDmlRows%2CEmail%2C%0A++++++++++LimitContext%2CLimitExceptions%2CMobilePush%2C%0A++++++++++QueryRows%2CSosl%2CCpu%2CDml%2CSoql%0A++++++++FROM+ApexTestResults%29%0AFROM+ApexTestResult%0AWHERE+AsyncApexJobId%3D%27{}%27%0A".format(
                job_id
            )
        )

    def _get_mock_testqueueitem_status_query_url(self, job_id):
        return (
            self.base_tooling_url
            + f"query/?q=SELECT+Id%2C+Status%2C+ExtendedStatus%2C+ApexClassId+FROM+ApexTestQueueItem+WHERE+ParentJobId+%3D+%27{job_id}%27+AND+Status+%3D+%27Failed%27"
        )

    def _mock_get_test_results(
        self, outcome="Pass", message="Test Passed", job_id="JOB_ID1234567"
    ):
        url = self._get_mock_test_query_url(job_id)

        expected_response = self._get_mock_test_query_results(
            ["TestMethod"], [outcome], [message]
        )
        responses.add(
            responses.GET, url, match_querystring=True, json=expected_response
        )

    def _mock_get_test_results_multiple(
        self, method_names, outcomes, messages, job_id="JOB_ID1234567"
    ):
        url = self._get_mock_test_query_url(job_id)

        expected_response = self._get_mock_test_query_results(
            method_names, outcomes, messages
        )
        responses.add(
            responses.GET, url, match_querystring=True, json=expected_response
        )

    def _mock_get_failed_test_classes(self, job_id="JOB_ID1234567"):
        url = self._get_mock_testqueueitem_status_query_url(job_id)

        responses.add(
            responses.GET,
            url,
            match_querystring=True,
            json={"totalSize": 0, "records": [], "done": True},
        )

    def _mock_get_failed_test_classes_failure(self, job_id="JOB_ID1234567"):
        url = self._get_mock_testqueueitem_status_query_url(job_id)

        responses.add(
            responses.GET,
            url,
            match_querystring=True,
            json={
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0000000000000000",
                        "ApexClassId": 1,
                        "Status": "Failed",
                        "ExtendedStatus": "Double-plus ungood",
                    }
                ],
                "done": True,
            },
        )

    def _mock_get_symboltable(self):
        url = (
            self.base_tooling_url
            + "query/?q=SELECT+SymbolTable+FROM+ApexClass+WHERE+Name%3D%27TestClass_TEST%27"
        )

        responses.add(
            responses.GET,
            url,
            json={
                "records": [
                    {
                        "SymbolTable": {
                            "methods": [
                                {"name": "test1", "annotations": [{"name": "isTest"}]}
                            ]
                        }
                    }
                ]
            },
        )

    def _mock_get_symboltable_failure(self):
        url = (
            self.base_tooling_url
            + "query/?q=SELECT+SymbolTable+FROM+ApexClass+WHERE+Name%3D%27TestClass_TEST%27"
        )

        responses.add(responses.GET, url, json={"records": []})

    def _mock_tests_complete(self, job_id="JOB_ID1234567"):
        url = (
            self.base_tooling_url
            + "query/?q=SELECT+Id%2C+Status%2C+"
            + "ApexClassId+FROM+ApexTestQueueItem+WHERE+ParentJobId+%3D+%27"
            + "{}%27".format(job_id)
        )
        expected_response = {
            "done": True,
            "totalSize": 1,
            "records": [{"Status": "Completed"}],
        }
        responses.add(
            responses.GET, url, match_querystring=True, json=expected_response
        )

    def _mock_tests_processing(self, job_id="JOB_ID1234567"):
        url = (
            self.base_tooling_url
            + "query/?q=SELECT+Id%2C+Status%2C+"
            + "ApexClassId+FROM+ApexTestQueueItem+WHERE+ParentJobId+%3D+%27"
            + "{}%27".format(job_id)
        )
        expected_response = {
            "done": True,
            "totalSize": 1,
            "records": [{"Status": "Processing", "ApexClassId": 1}],
        }
        responses.add(
            responses.GET, url, match_querystring=True, json=expected_response
        )

    def _mock_run_tests(self, success=True, body="JOB_ID1234567"):
        url = self.base_tooling_url + "runTestsAsynchronous"
        if success:
            responses.add(responses.POST, url, json=body)
        else:
            responses.add(responses.POST, url, status=http.client.SERVICE_UNAVAILABLE)

    @responses.activate
    def test_run_task(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_get_failed_test_classes()
        self._mock_tests_complete()
        self._mock_get_test_results()
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        task()
        assert len(responses.calls) == 5

    @responses.activate
    def test_run_task__server_error(self):
        self._mock_apex_class_query()
        self._mock_run_tests(success=False)
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        with pytest.raises(SalesforceGeneralError):
            task()

    @responses.activate
    def test_run_task__failed(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_get_failed_test_classes()
        self._mock_tests_complete()
        self._mock_get_test_results("Fail")
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        with pytest.raises(ApexTestException):
            task()

    @responses.activate
    def test_run_task__failed_class_level(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_get_failed_test_classes_failure()
        self._mock_tests_complete()
        self._mock_get_test_results()
        self._mock_get_symboltable()
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        with pytest.raises(ApexTestException):
            task()

    @responses.activate
    def test_run_task__failed_class_level_no_symboltable(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_get_failed_test_classes_failure()
        self._mock_tests_complete()
        self._mock_get_test_results()
        self._mock_get_symboltable_failure()
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        with pytest.raises(CumulusCIException):
            task()

    @responses.activate
    def test_run_task__failed_class_level_no_symboltable__spring20_managed(self):
        self._mock_apex_class_query(name="ns__Test_TEST", namespace="ns")
        self._mock_run_tests()
        self._mock_get_failed_test_classes_failure()
        self._mock_tests_complete()
        self._mock_get_test_results()
        self._mock_get_symboltable_failure()
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "managed": True,
            "namespace": "ns",
        }

        task = RunApexTests(self.project_config, task_config, self.org_config)
        task._get_test_methods_for_class = Mock()

        task()

        task._get_test_methods_for_class.assert_not_called()

    @responses.activate
    def test_run_task__retry_tests(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_run_tests(body="JOBID_9999")
        self._mock_get_failed_test_classes()
        self._mock_get_failed_test_classes(job_id="JOBID_9999")
        self._mock_tests_complete()
        self._mock_tests_complete(job_id="JOBID_9999")
        self._mock_get_test_results("Fail", "UNABLE_TO_LOCK_ROW")
        self._mock_get_test_results(job_id="JOBID_9999")

        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "retry_failures": ["UNABLE_TO_LOCK_ROW"],
        }
        task = RunApexTests(self.project_config, task_config, self.org_config)
        task()
        assert len(responses.calls) == 9

    @responses.activate
    def test_run_task__retry_tests_with_retry_always(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_run_tests(body="JOBID_9999")
        self._mock_run_tests(body="JOBID_9990")
        self._mock_get_failed_test_classes()
        self._mock_get_failed_test_classes(job_id="JOBID_9999")
        self._mock_get_failed_test_classes(job_id="JOBID_9990")
        self._mock_tests_complete()
        self._mock_tests_complete(job_id="JOBID_9999")
        self._mock_tests_complete(job_id="JOBID_9990")
        self._mock_get_test_results_multiple(
            ["TestOne", "TestTwo"],
            ["Fail", "Fail"],
            ["UNABLE_TO_LOCK_ROW", "LimitException"],
        )
        self._mock_get_test_results_multiple(
            ["TestOne"], ["Pass"], [""], job_id="JOBID_9999"
        )
        self._mock_get_test_results_multiple(
            ["TestTwo"], ["Fail"], ["LimitException"], job_id="JOBID_9990"
        )
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "retry_failures": ["UNABLE_TO_LOCK_ROW"],
            "retry_always": True,
        }
        task = RunApexTests(self.project_config, task_config, self.org_config)
        with pytest.raises(ApexTestException):
            task()

    @responses.activate
    def test_run_task__retry_tests_fails(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_run_tests(body="JOBID_9999")
        self._mock_get_failed_test_classes()
        self._mock_get_failed_test_classes(job_id="JOBID_9999")
        self._mock_tests_complete()
        self._mock_tests_complete(job_id="JOBID_9999")
        self._mock_get_test_results("Fail", "UNABLE_TO_LOCK_ROW")
        self._mock_get_test_results("Fail", "DUPLICATES_DETECTED", job_id="JOBID_9999")

        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "retry_failures": ["UNABLE_TO_LOCK_ROW"],
        }
        task = RunApexTests(self.project_config, task_config, self.org_config)
        with pytest.raises(ApexTestException):
            task()

    @responses.activate
    def test_run_task__processing(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_tests_processing()
        self._mock_get_failed_test_classes()
        self._mock_tests_complete()
        self._mock_get_test_results()
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        task()
        log = self._task_log_handler.messages
        assert "Completed: 0  Processing: 1 (TestClass_TEST)  Queued: 0" in log["info"]

    @responses.activate
    def test_run_task__not_verbose(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_tests_processing()
        self._mock_get_failed_test_classes()  # this returns all passes
        self._mock_tests_complete()
        self._mock_get_test_results()
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        task()
        log = self._task_log_handler.messages
        assert "Class: TestClass_TEST" not in log["info"]

    @responses.activate
    def test_run_task__verbose(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_get_failed_test_classes_failure()
        self._mock_tests_complete()
        self._mock_get_test_results()
        self._mock_get_symboltable()
        task_config = TaskConfig()
        task_config.config["options"] = {
            "verbose": True,
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
        }
        task = RunApexTests(self.project_config, task_config, self.org_config)
        with pytest.raises(CumulusCIException):
            task()
        log = self._task_log_handler.messages
        assert "Class: TestClass_TEST" in log["info"]

    @responses.activate
    def test_run_task__no_code_coverage(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_get_failed_test_classes()
        self._mock_tests_complete()
        self._mock_get_test_results()
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
        }
        task = RunApexTests(self.project_config, task_config, self.org_config)
        task._check_code_coverage = Mock()
        task()
        task._check_code_coverage.assert_not_called()

    @responses.activate
    def test_run_task__checks_code_coverage(self):
        self._mock_apex_class_query()
        self._mock_run_tests()
        self._mock_get_failed_test_classes()
        self._mock_tests_complete()
        self._mock_get_test_results()
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "required_org_code_coverage_percent": "90",
        }

        org_config = OrgConfig(
            {
                "id": "foo/1",
                "instance_url": "https://example.com",
                "access_token": "abc123",
            },
            "test",
        )
        org_config._installed_packages = {"TEST": StrictVersion("1.2.3")}
        task = RunApexTests(self.project_config, task_config, org_config)
        task._check_code_coverage = Mock()
        task()
        task._check_code_coverage.assert_called_once()

    def test_code_coverage_integer(self):
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "required_org_code_coverage_percent": 90,
        }

        org_config = OrgConfig(
            {
                "id": "foo/1",
                "instance_url": "https://example.com",
                "access_token": "abc123",
            },
            "test",
        )
        task = RunApexTests(self.project_config, task_config, org_config)

        assert task.code_coverage_level == 90

    def test_code_coverage_percentage(self):
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "required_org_code_coverage_percent": "90%",
        }

        org_config = OrgConfig(
            {
                "id": "foo/1",
                "instance_url": "https://example.com",
                "access_token": "abc123",
            },
            "test",
        )
        task = RunApexTests(self.project_config, task_config, org_config)

        assert task.code_coverage_level == 90

    def test_exception_bad_code_coverage(self):
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "required_org_code_coverage_percent": "foo",
        }

        with pytest.raises(TaskOptionsError):
            RunApexTests(self.project_config, task_config, self.org_config)

    @responses.activate
    def test_run_task__code_coverage_managed(self):
        self._mock_apex_class_query(namespace="TEST")
        self._mock_run_tests()
        self._mock_get_failed_test_classes()
        self._mock_tests_complete()
        self._mock_get_test_results()
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "namespace": "TEST",
            "required_org_code_coverage_percent": "90",
        }
        org_config = OrgConfig(
            {
                "id": "foo/1",
                "instance_url": "https://example.com",
                "access_token": "abc123",
            },
            "test",
        )
        org_config._installed_packages = {"TEST": StrictVersion("1.2.3")}

        task = RunApexTests(self.project_config, task_config, org_config)
        task._check_code_coverage = Mock()
        task()
        task._check_code_coverage.assert_not_called()

    def test_check_code_coverage(self):
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        task.code_coverage_level = 90
        task.tooling = Mock()
        task.tooling.query.return_value = {
            "records": [{"PercentCovered": 90}],
            "totalSize": 1,
        }

        task._check_code_coverage()
        task.tooling.query.assert_called_once_with(
            "SELECT PercentCovered FROM ApexOrgWideCoverage"
        )

    def test_check_code_coverage__fail(self):
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        task.code_coverage_level = 90
        task.tooling = Mock()
        task.tooling.query.return_value = {
            "records": [{"PercentCovered": 89}],
            "totalSize": 1,
        }

        with pytest.raises(ApexTestException):
            task._check_code_coverage()

    def test_is_retriable_failure(self):
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "retry_failures": [
                "UNABLE_TO_LOCK_ROW",
                "unable to obtain exclusive access to this record",
            ],
        }
        task = RunApexTests(self.project_config, task_config, self.org_config)
        task._init_options(task_config.config["options"])

        assert task._is_retriable_failure(
            {
                "Message": "UNABLE_TO_LOCK_ROW",
                "StackTrace": "test",
                "Outcome": "Fail",
            }
        )
        assert task._is_retriable_failure(
            {
                "Message": "TEST",
                "StackTrace": "unable to obtain exclusive access to this record",
                "Outcome": "Fail",
            }
        )
        assert not task._is_retriable_failure(
            {
                "Message": "DUPLICATES_DETECTED",
                "StackTrace": "test",
                "Outcome": "Fail",
            }
        )

    def test_init_options__regexes(self):
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "retry_failures": ["UNABLE_TO_LOCK_ROW"],
        }
        task = RunApexTests(self.project_config, task_config, self.org_config)
        task._init_options(task_config.config["options"])

        assert (
            task.options["retry_failures"][0].search("UNABLE_TO_LOCK_ROW: test failed")
            is not None
        )

    def test_init_options__bad_regexes(self):
        task_config = TaskConfig()
        task_config.config["options"] = {
            "junit_output": "results_junit.xml",
            "poll_interval": 1,
            "test_name_match": "%_TEST",
            "retry_failures": ["("],
        }
        with pytest.raises(TaskOptionsError):
            task = RunApexTests(self.project_config, task_config, self.org_config)
            task._init_options(task_config.config["options"])

    def test_get_namespace_filter__managed(self):
        task_config = TaskConfig({"options": {"managed": True, "namespace": "testns"}})
        task = RunApexTests(self.project_config, task_config, self.org_config)
        namespace = task._get_namespace_filter()
        assert namespace == "'testns'"

    def test_get_namespace_filter__managed_no_namespace(self):
        task_config = TaskConfig({"options": {"managed": True}})
        task = RunApexTests(self.project_config, task_config, self.org_config)
        with pytest.raises(TaskOptionsError):
            task._get_namespace_filter()

    def test_get_test_class_query__exclude(self):
        task_config = TaskConfig(
            {"options": {"test_name_match": "%_TEST", "test_name_exclude": "EXCL"}}
        )
        task = RunApexTests(self.project_config, task_config, self.org_config)
        query = task._get_test_class_query()
        assert (
            "SELECT Id, Name FROM ApexClass WHERE NamespacePrefix = null "
            "AND (Name LIKE '%_TEST') AND (NOT Name LIKE 'EXCL')" == query
        )

    def test_run_task__no_tests(self):
        task = RunApexTests(self.project_config, self.task_config, self.org_config)
        task._get_test_classes = MagicMock(return_value={"totalSize": 0})
        task()
        assert task.result is None


@patch(
    "cumulusci.core.tasks.BaseSalesforceTask._update_credentials",
    MagicMock(return_value=None),
)
class TestAnonymousApexTask:
    def setup_method(self):
        self.api_version = 42.0
        self.universal_config = UniversalConfig(
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
            "param1": "StringValue",
        }
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.project_config.config = {
            "project": {
                "package": {"namespace": "abc", "api_version": self.api_version}
            }
        }
        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)
        self.org_config = OrgConfig(
            {
                "id": "foo/1",
                "instance_url": "https://example.com",
                "access_token": "abc123",
                "namespace": "abc",
            },
            "test",
        )
        self.org_config._installed_packages = {}
        self.base_tooling_url = "{}/services/data/v{}/tooling/".format(
            self.org_config.instance_url, self.api_version
        )

    def teardown_method(self):
        shutil.rmtree(self.tmpdir)

    def _get_url_and_task(self):
        task = AnonymousApexTask(self.project_config, self.task_config, self.org_config)
        url = self.base_tooling_url + "executeAnonymous"
        return task, url

    def test_validate_options(self):
        task_config = TaskConfig({})
        with pytest.raises(TaskOptionsError):
            AnonymousApexTask(self.project_config, task_config, self.org_config)

    def test_run_from_path_outside_repo(self):
        task_config = TaskConfig({"options": {"path": "/"}})
        task = AnonymousApexTask(self.project_config, task_config, self.org_config)
        with pytest.raises(TaskOptionsError):
            task()

    def test_run_path_not_found(self):
        task_config = TaskConfig({"options": {"path": "bogus"}})
        task = AnonymousApexTask(self.project_config, task_config, self.org_config)
        with pytest.raises(TaskOptionsError):
            task()

    def test_prepare_apex(self):
        self.task_config.config["options"]["namespaced"] = True

        task = AnonymousApexTask(self.project_config, self.task_config, self.org_config)
        before = "String %%%NAMESPACED_ORG%%%str = '%%%NAMESPACED_RT%%%';"
        expected = "String abc__str = 'abc.';"
        assert expected == task._prepare_apex(before)

    def test_prepare_apex__detect_namespace(self):
        task = AnonymousApexTask(self.project_config, self.task_config, self.org_config)
        before = "String %%%NAMESPACED_ORG%%%str = '%%%NAMESPACED_RT%%%';"
        expected = "String abc__str = 'abc.';"
        assert expected == task._prepare_apex(before)

    def test_optional_parameter_1_replacement(self):
        task = AnonymousApexTask(self.project_config, self.task_config, self.org_config)
        before = "String str = '%%%PARAM_1%%%';"
        expected = "String str = 'StringValue';"
        assert expected == task._prepare_apex(before)

    def test_optional_parameter_2_replacement(self):
        task = AnonymousApexTask(self.project_config, self.task_config, self.org_config)
        before = "String str = '%%%PARAM_2%%%';"
        expected = "String str = '';"
        assert expected == task._prepare_apex(before)

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
        url = self.base_tooling_url + "executeAnonymous"
        responses.add(
            responses.GET, url, status=200, json={"compiled": True, "success": True}
        )
        task()

    @responses.activate
    def test_run_anonymous_apex_status_fail(self):
        task, url = self._get_url_and_task()
        responses.add(responses.GET, url, status=418, body="I'm a teapot")
        with pytest.raises(SalesforceGeneralError) as e:
            task()
        err = e.value
        assert str(err) == "Error Code 418. Response content: I'm a teapot"
        assert err.url.startswith(url)
        assert err.status == 418
        assert err.content == "I'm a teapot"

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
        with pytest.raises(ApexCompilationException) as e:
            task()
        err = e.value
        assert err.args[0] == 1
        assert err.args[1] == problem

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
        with pytest.raises(ApexException) as e:
            task()
        err = e.value
        assert err.args[0] == problem
        assert err.args[1] == trace

    @responses.activate
    def test_run_anonymous_apex__gack(self):
        task, url = self._get_url_and_task()
        responses.add(responses.GET, url, status=200, body="null")
        with pytest.raises(SalesforceException) as e:
            task()
        err = str(e.value)
        assert "gack" in err


@patch(
    "cumulusci.core.tasks.BaseSalesforceTask._update_credentials",
    MagicMock(return_value=None),
)
class TestRunBatchApex(MockLoggerMixin):
    def setup_method(self):
        self.api_version = 42.0
        self.universal_config = UniversalConfig(
            {"project": {"api_version": self.api_version}}
        )
        self.task_config = TaskConfig()
        self.task_config.config["options"] = {
            "class_name": "ADDR_Seasonal_BATCH",
            "poll_interval": 1,
        }
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.project_config.config["project"] = {
            "package": {"api_version": self.api_version}
        }
        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)
        self.org_config = OrgConfig(
            {
                "id": "foo/1",
                "instance_url": "https://example.com",
                "access_token": "abc123",
            },
            "test",
        )
        self.base_tooling_url = "{}/services/data/v{}/tooling/".format(
            self.org_config.instance_url, self.api_version
        )
        self.task_log = self._task_log_handler.messages

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

    def _update_job_result(self, response: dict, result_dict: dict):
        "Extend the result from _get_query_resp with additional batch records"
        template_result = response["records"][-1]  # use the last result as a template
        assert isinstance(template_result, dict)
        new_result = {**template_result, **result_dict}  # copy with variations
        old_subjob_results = [  # set completed for all old subjob results
            {**record, "Status": "Completed"} for record in response["records"]
        ]
        result_list = [
            new_result
        ] + old_subjob_results  # prepend new result because SOQL is order by DESC
        return {**response, "records": result_list}

    def _get_url_and_task(self):
        task = BatchApexWait(self.project_config, self.task_config, self.org_config)
        url = (
            self.base_tooling_url
            + "query/?q=SELECT+Id%2C+ApexClass.Name%2C+Status%2C+ExtendedStatus%2C+TotalJobItems%2C+JobItemsProcessed%2C+NumberOfErrors%2C+CreatedDate%2C+CompletedDate+FROM+AsyncApexJob+WHERE+JobType+IN+%28%27BatchApex%27%2C%27Queueable%27%29+AND+ApexClass.Name%3D%27ADDR_Seasonal_BATCH%27++++ORDER+BY+CreatedDate+DESC++LIMIT+1+"
        )
        return task, url

    @responses.activate
    def test_run_batch_apex_status_fail(self):
        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"][0]["NumberOfErrors"] = 1
        response["records"][0]["ExtendedStatus"] = "Bad Status"
        responses.add(responses.GET, url, json=response)
        with pytest.raises(SalesforceException) as e:
            task()
        err = e.value
        assert "Bad Status" in err.args[0]

    @responses.activate
    def test_run_batch_apex_number_mismatch(self):
        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"][0]["JobItemsProcessed"] = 1
        response["records"][0]["TotalJobItems"] = 3
        responses.add(responses.GET, url, json=response)
        task()

        assert "The final record counts do not add up." in self.task_log["info"]

    @responses.activate
    def test_run_batch_apex_status_ok(self):
        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        responses.add(responses.GET, url, json=response)
        task()

    @responses.activate
    def test_run_batch_apex_calc_elapsed_time(self):
        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        responses.add(responses.GET, url, json=response)
        task()
        assert task.elapsed_time(task.subjobs) == 61

    @responses.activate
    def test_run_batch_apex_queueable_status_failed(self):
        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"][0]["JobType"] = "Queueable"
        response["records"][0]["Status"] = "Failed"
        response["records"][0]["JobItemsProcessed"] = 0
        response["records"][0]["TotalJobItems"] = 0
        response["records"][0]["ExtendedStatus"] = "Error Details"
        responses.add(responses.GET, url, json=response)
        with pytest.raises(SalesforceException) as e:
            task()
        assert "failure" in str(e.value)

    @responses.activate
    def test_run_batch_apex_status_aborted(self):
        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"][0]["Status"] = "Aborted"
        response["records"][0]["JobItemsProcessed"] = 1
        response["records"][0]["TotalJobItems"] = 3
        responses.add(responses.GET, url, json=response)
        with pytest.raises(SalesforceException) as e:
            task()
        assert "aborted" in str(e.value)

    @responses.activate
    def test_run_batch_apex_status_failed(self):
        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"][0]["Status"] = "Failed"
        response["records"][0]["JobItemsProcessed"] = 1
        response["records"][0]["TotalJobItems"] = 3
        responses.add(responses.GET, url, json=response)
        self.task_log["info"] = []
        with pytest.raises(SalesforceException) as e:
            task()
        assert "failure" in str(e.value)

    @responses.activate
    def test_chained_subjobs(self):
        "Test subjobs that kick off a successor before they complete"
        task, url = self._get_url_and_task()
        url2 = (
            url.split("?")[0]
            + "?q=SELECT+Id%2C+ApexClass.Name%2C+Status%2C+ExtendedStatus%2C+TotalJobItems%2C+JobItemsProcessed%2C+NumberOfErrors%2C+CreatedDate%2C+CompletedDate+FROM+AsyncApexJob+WHERE+JobType+IN+%28%27BatchApex%27%2C%27Queueable%27%29+AND+ApexClass.Name%3D%27ADDR_Seasonal_BATCH%27++AND+CreatedDate+%3E%3D+2018-08-07T16%3A00%3A00Z++ORDER+BY+CreatedDate+DESC++"
        )

        # batch 1
        response = self._get_query_resp()
        batch_record = response["records"][0]
        batch_record.update(
            {
                "JobItemsProcessed": 1,
                "TotalJobItems": 3,
                "NumberOfErrors": 0,
                "Status": "Processing",
                "CreatedDate": "2018-08-07T16:00:00.000+0000",
            }
        )

        responses.add(responses.GET, url, json=response)

        # batch 2: 1 error
        response = self._update_job_result(
            response, {"Id": "Id2", "NumberOfErrors": 1, "Status": "Processing"}
        )
        responses.add(responses.GET, url2, json=response)

        # batch 3: found another error
        response = self._update_job_result(
            response, {"Id": "Id2", "NumberOfErrors": 2, "Status": "Processing"}
        )
        responses.add(responses.GET, url2, json=response)

        # batch 4: Complete, no errors in this sub-batch
        response = self._update_job_result(
            response,
            {
                "NumberOfErrors": 0,
                "Id": "Id4",
                "Status": "Completed",
                "CompletedDate": "2018-08-07T16:10:00.000+0000",  # 10 minutes passed
            },
        )
        responses.add(responses.GET, url2, json=response.copy())

        with pytest.raises(SalesforceException) as e:
            task()

        assert len(task.subjobs) == 4
        summary = task.summarize_subjobs(task.subjobs)
        assert not summary["Success"]
        assert not summary["CountsAddUp"]
        assert summary["ElapsedTime"] == 10 * 60
        assert summary["JobItemsProcessed"] == 4
        assert summary["TotalJobItems"] == 12
        assert summary["NumberOfErrors"] == 3
        assert "batch errors" in str(e.value)

    @responses.activate
    def test_chained_subjobs_beginning(self):
        "Test the first subjob that kicks off a successor before they complete"
        task, url = self._get_url_and_task()
        url2 = (
            url.split("?")[0]
            + "?q=SELECT+Id%2C+ApexClass.Name%2C+Status%2C+ExtendedStatus%2C+TotalJobItems%2C+JobItemsProcessed%2C+NumberOfErrors%2C+CreatedDate%2C+CompletedDate+FROM+AsyncApexJob+WHERE+JobType+IN+%28%27BatchApex%27%2C%27Queueable%27%29+AND+ApexClass.Name%3D%27ADDR_Seasonal_BATCH%27++AND+CreatedDate+%3E%3D+2018-08-07T16%3A00%3A00Z++ORDER+BY+CreatedDate+DESC++"
        )

        # batch 1
        response = self._get_query_resp()
        responses.add(responses.GET, url2, json=response)

        batch_record = response["records"][0]
        batch_record.update(
            {
                "JobItemsProcessed": 1,
                "TotalJobItems": 3,
                "NumberOfErrors": 0,
                "Status": "Preparing",
                "CreatedDate": "2018-08-07T16:00:00.000+0000",
                "CompletedDate": None,
            }
        )

        real_poll_action = task._poll_action
        counter = 0

        def mock_poll_action():
            nonlocal counter
            counter += 1
            if counter == 1:
                task.poll_complete = False
                return real_poll_action()
            else:
                rc = real_poll_action()
                task.poll_complete = True
                return rc

        task._poll_action = mock_poll_action

        responses.add(responses.GET, url, json=response)

        task()
        assert counter == 2
        assert task.poll_complete
        summary = task.summarize_subjobs(task.subjobs)
        assert not summary["NumberOfErrors"]

    @responses.activate
    def test_chained_subjobs_halfway(self):
        "Test part-way through a series of subjobs that kick off a successor before they complete"
        task, url = self._get_url_and_task()
        url2 = (
            url.split("?")[0]
            + "?q=SELECT+Id%2C+ApexClass.Name%2C+Status%2C+ExtendedStatus%2C+TotalJobItems%2C+JobItemsProcessed%2C+NumberOfErrors%2C+CreatedDate%2C+CompletedDate+FROM+AsyncApexJob+WHERE+JobType+IN+%28%27BatchApex%27%2C%27Queueable%27%29+AND+ApexClass.Name%3D%27ADDR_Seasonal_BATCH%27++AND+CreatedDate+%3E%3D+2018-08-07T16%3A00%3A00Z++ORDER+BY+CreatedDate+DESC++"
        )

        # batch 1
        response = self._get_query_resp()
        responses.add(responses.GET, url2, json=response)

        batch_record = response["records"][0]
        batch_record.update(
            {
                "JobItemsProcessed": 1,
                "TotalJobItems": 3,
                "NumberOfErrors": 0,
                "Status": "Preparing",
                "CreatedDate": "2018-08-07T16:00:00.000+0000",
                "CompletedDate": "2018-08-07T16:05:00.000+0000",
            }
        )

        # batch 2: 1 error
        response = self._update_job_result(
            response, {"Id": "Id2", "NumberOfErrors": 1, "CompletedDate": None}
        )
        responses.add(responses.GET, url2, json=response)

        real_poll_action = task._poll_action
        counter = 0

        def mock_poll_action():
            nonlocal counter
            counter += 1
            if counter == 1:
                task.poll_complete = False
                return real_poll_action()
            else:
                rc = real_poll_action()
                task.poll_complete = True
                return rc

        task._poll_action = mock_poll_action

        responses.add(responses.GET, url, json=response)

        task()
        assert counter == 2
        assert task.poll_complete
        summary = task.summarize_subjobs(task.subjobs)
        assert not summary["NumberOfErrors"]

    @responses.activate
    def test_job_not_found(self):

        task, url = self._get_url_and_task()
        response = self._get_query_resp()
        response["records"] = []
        responses.add(responses.GET, url, json=response)

        with pytest.raises(SalesforceException) as e:
            task()

        assert "found" in str(e.value)


class TestApexIntegrationTests:
    @pytest.mark.org_shape("qa", "ccitest:qa_org")
    @pytest.mark.slow()
    @pytest.mark.skip()  # until our CI has access to github service, or test
    # doesn't rely on it. In the meantime, the VCR test below is still good
    # and this test works on laptops.
    def test_run_tests__integration_test__call_salesforce(self, create_task, caplog):
        self._test_run_tests__integration_test(create_task, caplog)

    # There were challenges VCR-ing this because it depends on a
    # particular flow. To recreate the tape you'll need to run the
    # ccitest:qa_org flow aginst your org first.
    #
    # Also: some redundant "polls" were removed by hand to avoid
    # disk space usage.
    def test_run_tests__integration_test(self, create_task, caplog, vcr):
        with vcr.use_cassette(
            "ManualEditTestApexIntegrationTests.test_run_tests__integration_test.yaml",
            record_mode="none",
        ):
            self._test_run_tests__integration_test(create_task, caplog)

    def _test_run_tests__integration_test(self, create_task, caplog):

        caplog.set_level(logging.INFO)
        with pytest.raises(exc.ApexTestException) as e:
            task = create_task(
                RunApexTests,
                {
                    "required_org_code_coverage_percent": 70,
                    "required_per_class_code_coverage_percent": 60,
                    "json_output": None,
                    "junit_output": None,
                },
            )
            with patch.object(task, "_update_credentials"):
                task()
        relevant_records = [
            record for record in caplog.records if "below required level" in str(record)
        ]
        assert len(relevant_records) == 1, caplog.records
        assert "SampleClass2" in str(relevant_records[0])
        assert "below required level" in str(e.value)
        assert "SampleClass2" in str(e.value)

        caplog.clear()

        task = create_task(
            RunApexTests,
            {
                "required_org_code_coverage_percent": 70,
                "required_per_class_code_coverage_percent": 40,
                "json_output": None,
                "junit_output": None,
            },
        )
        with patch.object(task, "_update_credentials"):
            task()
        relevant_records = [
            record for record in caplog.records if "expectations" in str(record)
        ]
        assert len(relevant_records) == 2
        assert "All classes meet" in str(relevant_records)
        assert "Organization-wide code" in str(relevant_records)
