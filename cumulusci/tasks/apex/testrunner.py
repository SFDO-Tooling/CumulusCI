""" CumulusCI Tasks for running Apex Tests """

import html
import io
import json
import re

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import (
    TaskOptionsError,
    ApexTestException,
    CumulusCIException,
)
from cumulusci.core.utils import process_bool_arg, process_list_arg, decode_to_unicode

APEX_LIMITS = {
    "Soql": {
        "Label": "TESTING_LIMITS: Number of SOQL queries",
        "SYNC": 100,
        "ASYNC": 200,
    },
    "Email": {
        "Label": "TESTING_LIMITS: Number of Email Invocations",
        "SYNC": 10,
        "ASYNC": 10,
    },
    "AsyncCalls": {
        "Label": "TESTING_LIMITS: Number of future calls",
        "SYNC": 50,
        "ASYNC": 50,
    },
    "DmlRows": {
        "Label": "TESTING_LIMITS: Number of DML rows",
        "SYNC": 10000,
        "ASYNC": 10000,
    },
    "Cpu": {"Label": "TESTING_LIMITS: Maximum CPU time", "SYNC": 10000, "ASYNC": 60000},
    "QueryRows": {
        "Label": "TESTING_LIMITS: Number of query rows",
        "SYNC": 50000,
        "ASYNC": 50000,
    },
    "Dml": {
        "Label": "TESTING_LIMITS: Number of DML statements",
        "SYNC": 150,
        "ASYNC": 150,
    },
    "MobilePush": {
        "Label": "TESTING_LIMITS: Number of Mobile Apex push calls",
        "SYNC": 10,
        "ASYNC": 10,
    },
    "Sosl": {
        "Label": "TESTING_LIMITS: Number of SOSL queries",
        "SYNC": 20,
        "ASYNC": 20,
    },
    "Callouts": {
        "Label": "TESTING_LIMITS: Number of callouts",
        "SYNC": 100,
        "ASYNC": 100,
    },
}


TEST_RESULT_QUERY = """
SELECT Id,ApexClassId,TestTimestamp,
       Message,MethodName,Outcome,
       RunTime,StackTrace,
       (SELECT
          Id,Callouts,AsyncCalls,DmlRows,Email,
          LimitContext,LimitExceptions,MobilePush,
          QueryRows,Sosl,Cpu,Dml,Soql
        FROM ApexTestResults)
FROM ApexTestResult
WHERE AsyncApexJobId='{}'
"""


class RunApexTests(BaseSalesforceApiTask):
    """ Task to run Apex tests with the Tooling API and report results.

    This task optionally supports retrying unit tests that fail due to
    transitory issues or concurrency-related row locks. To enable retries,
    add ones or more regular expressions to the list option `retry_failures`.

    When a test run fails, if all of the failures' error messages or stack traces
    match one of these regular expressions, each failed test will be retried by
    itself. This is often useful when running Apex tests in parallel; row locks
    may automatically be retried. Note that retries are supported whether or not
    the org has parallel Apex testing enabled.

    The ``retry_always`` option modifies this behavior: if a test run fails and
    any (not all) of the failures match the specified regular expressions,
    all of the failed tests will be retried in serial. This is helpful when
    underlying row locking errors are masked by custom exceptions.

    A useful base configuration for projects wishing to use retries is:

    .. code-block:: yaml

        retry_failures:
            - "unable to obtain exclusive access to this record"
            - "UNABLE_TO_LOCK_ROW"
            - "connection was cancelled here"
        retry_always: True

    Some projects' unit tests produce so many concurrency errors that
    it's faster to execute the entire run in serial mode than to use retries.
    Serial and parallel mode are configured in the scratch org definition file.
"""

    api_version = "38.0"
    name = "RunApexTests"
    task_options = {
        "test_name_match": {
            "description": (
                "Pattern to find Apex test classes to run "
                '("%" is wildcard).  Defaults to '
                "project__test__name_match from project config. "
                "Comma-separated list for multiple patterns."
            ),
            "required": True,
        },
        "test_name_exclude": {
            "description": (
                "Query to find Apex test classes to exclude "
                '("%" is wildcard).  Defaults to '
                "project__test__name_exclude from project config. "
                "Comma-separated list for multiple patterns."
            )
        },
        "namespace": {
            "description": (
                "Salesforce project namespace.  Defaults to "
                + "project__package__namespace"
            )
        },
        "managed": {
            "description": (
                "If True, search for tests in the namespace "
                + "only.  Defaults to False"
            )
        },
        "poll_interval": {
            "description": ("Seconds to wait between polling for Apex test results.")
        },
        "junit_output": {
            "description": "File name for JUnit output.  Defaults to test_results.xml"
        },
        "json_output": {
            "description": "File name for json output.  Defaults to test_results.json"
        },
        "retry_failures": {
            "description": "A list of regular expression patterns to match against "
            "test failures. If failures match, the failing tests are retried in "
            "serial mode."
        },
        "retry_always": {
            "description": "By default, all failures must match retry_failures to perform "
            "a retry. Set retry_always to True to retry all failed tests if any failure matches."
        },
        "required_org_code_coverage_percent": {
            "description": "Require at least X percent code coverage across the org following the test run."
        },
        "verbose": {
            "description": "By default, only failures get detailed output. "
            "Set verbose to True to see all passed test methods."
        },
    }

    def _init_options(self, kwargs):
        super(RunApexTests, self)._init_options(kwargs)

        self.options["test_name_match"] = self.options.get(
            "test_name_match", self.project_config.project__test__name_match
        )

        self.options["test_name_exclude"] = self.options.get(
            "test_name_exclude", self.project_config.project__test__name_exclude
        )

        if self.options["test_name_exclude"] is None:
            self.options["test_name_exclude"] = ""

        self.options["namespace"] = self.options.get(
            "namespace", self.project_config.project__package__namespace
        )

        self.options["junit_output"] = self.options.get(
            "junit_output", "test_results.xml"
        )

        self.options["json_output"] = self.options.get(
            "json_output", "test_results.json"
        )

        self.options["managed"] = process_bool_arg(self.options.get("managed", False))

        self.options["retry_failures"] = process_list_arg(
            self.options.get("retry_failures", [])
        )
        compiled_res = []
        for regex in self.options["retry_failures"]:
            try:
                compiled_res.append(re.compile(regex))
            except re.error as e:
                raise TaskOptionsError(
                    "An invalid regular expression ({}) was provided ({})".format(
                        regex, e
                    )
                )
        self.options["retry_failures"] = compiled_res
        self.options["retry_always"] = process_bool_arg(
            self.options.get("retry_always", False)
        )
        self.verbose = process_bool_arg(self.options.get("verbose", False))

        self.counts = {}

        if "required_org_code_coverage_percent" in self.options:
            try:
                self.code_coverage_level = int(
                    str(self.options["required_org_code_coverage_percent"]).rstrip("%")
                )
            except ValueError:
                raise TaskOptionsError(
                    f"Invalid code coverage level {self.options['required_org_code_coverage_percent']}"
                )
        else:
            self.code_coverage_level = None

    # pylint: disable=W0201
    def _init_class(self):
        self.classes_by_id = {}
        self.classes_by_name = {}
        self.job_id = None
        self.results_by_class_name = {}
        self.result = None
        self.retry_details = None

    def _get_namespace_filter(self):
        if self.options["managed"]:
            namespace = self.options.get("namespace")
            if not namespace:
                raise TaskOptionsError(
                    "Running tests in managed mode but no namespace available."
                )
            namespace = "'{}'".format(namespace)
        else:
            namespace = "null"
        return namespace

    def _get_test_class_query(self):
        namespace = self._get_namespace_filter()
        # Split by commas to allow multiple class name matching options
        test_name_match = self.options["test_name_match"]
        included_tests = []
        for pattern in test_name_match.split(","):
            if pattern:
                included_tests.append("Name LIKE '{}'".format(pattern))
        # Add any excludes to the where clause
        test_name_exclude = self.options.get("test_name_exclude", "")
        excluded_tests = []
        for pattern in test_name_exclude.split(","):
            if pattern:
                excluded_tests.append("(NOT Name LIKE '{}')".format(pattern))
        # Get all test classes for namespace
        query = "SELECT Id, Name FROM ApexClass " + "WHERE NamespacePrefix = {}".format(
            namespace
        )
        if included_tests:
            query += " AND ({})".format(" OR ".join(included_tests))
        if excluded_tests:
            query += " AND {}".format(" AND ".join(excluded_tests))
        return query

    def _get_test_classes(self):
        query = self._get_test_class_query()
        # Run the query
        self.logger.info("Running query: {}".format(query))
        result = self.tooling.query_all(query)
        self.logger.info("Found {} test classes".format(result["totalSize"]))
        return result

    def _get_test_methods_for_class(self, class_name):
        result = self.tooling.query(
            f"SELECT SymbolTable FROM ApexClass WHERE Name='{class_name}'"
        )
        test_methods = []

        try:
            methods = result["records"][0]["SymbolTable"]["methods"]
        except (TypeError, IndexError, KeyError):
            raise CumulusCIException(
                f"Unable to acquire symbol table for failed Apex class {class_name}"
            )
        for m in methods:
            for a in m.get("annotations", []):
                if a["name"].lower() in ["istest", "testmethod"]:
                    test_methods.append(m["name"])
                    break

        return test_methods

    def _is_retriable_error_message(self, error_message):
        return any(
            [reg.search(error_message) for reg in self.options["retry_failures"]]
        )

    def _is_retriable_failure(self, test_result):
        return self._is_retriable_error_message(
            test_result["Message"] or ""
        ) or self._is_retriable_error_message(test_result["StackTrace"] or "")

    def _get_test_results(self, allow_retries=True):
        # We need to query at both the test result and test queue item level.
        # Some concurrency problems manifest as all or part of the class failing,
        # without leaving behind any visible ApexTestResult records.
        # See https://salesforce.stackexchange.com/questions/262893/any-way-to-get-consistent-test-counts-when-parallel-testing-is-used

        # First, gather the Ids of failed test classes.
        test_classes = self.tooling.query_all(
            "SELECT Id, Status, ExtendedStatus, ApexClassId FROM ApexTestQueueItem "
            + "WHERE ParentJobId = '{}' AND Status = 'Failed'".format(self.job_id)
        )
        class_level_errors = {
            each_class["ApexClassId"]: each_class["ExtendedStatus"]
            for each_class in test_classes["records"]
        }

        result = self.tooling.query_all(TEST_RESULT_QUERY.format(self.job_id))

        if allow_retries:
            self.retry_details = {}

        for test_result in result["records"]:
            class_name = self.classes_by_id[test_result["ApexClassId"]]
            self.results_by_class_name[class_name][
                test_result["MethodName"]
            ] = test_result
            self.counts[test_result["Outcome"]] += 1

        # If we have class-level failures that did not come with line-level
        # failure details, report those as well.
        for class_id, error in class_level_errors.items():
            class_name = self.classes_by_id[class_id]

            self.logger.error(
                f"Class {class_name} failed to run some tests with the message {error}. Applying error to unit test results."
            )

            # In Spring '20, we cannot get symbol tables for managed classes.
            if self.options["managed"]:
                self.logger.error(
                    f"Cannot access symbol table for managed class {class_name}. Failure will not be retried."
                )
                continue

            # Get all the method names for this class
            test_methods = self._get_test_methods_for_class(class_name)
            for test_method in test_methods:
                # If this method was not run due to a class-level failure,
                # synthesize a failed result.
                # If we're retrying and fail again, do the same.
                if (
                    test_method not in self.results_by_class_name[class_name]
                    or self.results_by_class_name[class_name][test_method]["Outcome"]
                    == "Fail"
                ):
                    self.results_by_class_name[class_name][test_method] = {
                        "ApexClassId": class_id,
                        "MethodName": test_method,
                        "Outcome": "Fail",
                        "Message": f"Containing class {class_name} failed with message {error}",
                        "StackTrace": "",
                        "RunTime": 0,
                    }
                    self.counts["Fail"] += 1

        if allow_retries:
            for class_name, results in self.results_by_class_name.items():
                for test_result in results.values():
                    # Determine whether this failure is retriable.
                    if test_result["Outcome"] == "Fail" and allow_retries:
                        can_retry_this_failure = self._is_retriable_failure(test_result)
                        if can_retry_this_failure:
                            self.counts["Retriable"] += 1

                        # Even if this failure is not retriable per se,
                        # persist its details if we might end up retrying
                        # all failures.
                        if self.options["retry_always"] or can_retry_this_failure:
                            self.retry_details.setdefault(
                                test_result["ApexClassId"], []
                            ).append(test_result["MethodName"])

    def _process_test_results(self):
        test_results = []
        class_names = list(self.results_by_class_name.keys())
        class_names.sort()
        for class_name in class_names:
            has_failures = any(
                result["Outcome"] in ["Fail", "CompileFail"]
                for result in self.results_by_class_name[class_name].values()
            )
            if has_failures or self.verbose:
                self.logger.info(f"Class: {class_name}")
            method_names = list(self.results_by_class_name[class_name].keys())
            method_names.sort()
            for method_name in method_names:
                result = self.results_by_class_name[class_name][method_name]
                message = f"\t{result['Outcome']}: {result['MethodName']}"
                duration = result["RunTime"]
                result["stats"] = self._get_stats_from_result(result)
                if duration:
                    message += f" ({duration}ms)"
                test_results.append(
                    {
                        "Children": result.get("children", None),
                        "ClassName": decode_to_unicode(class_name),
                        "Method": decode_to_unicode(result["MethodName"]),
                        "Message": decode_to_unicode(result["Message"]),
                        "Outcome": decode_to_unicode(result["Outcome"]),
                        "StackTrace": decode_to_unicode(result["StackTrace"]),
                        "Stats": result.get("stats", None),
                        "TestTimestamp": result.get("TestTimestamp", None),
                    }
                )
                if result["Outcome"] in ["Fail", "CompileFail"]:
                    self.logger.info(message)
                    self.logger.info(f"\tMessage: {result['Message']}")
                    self.logger.info(f"\tStackTrace: {result['StackTrace']}")
                elif self.verbose:
                    self.logger.info(message)
        self.logger.info("-" * 80)
        self.logger.info(
            "Pass: {}  Retried: {}  Fail: {}  CompileFail: {}  Skip: {}".format(
                self.counts["Pass"],
                self.counts["Retriable"],
                self.counts["Fail"],
                self.counts["CompileFail"],
                self.counts["Skip"],
            )
        )
        self.logger.info("-" * 80)
        if self.counts["Fail"] or self.counts["CompileFail"]:
            self.logger.error("-" * 80)
            self.logger.error("Failing Tests")
            self.logger.error("-" * 80)
            counter = 0
            for result in test_results:
                if result["Outcome"] in ["Fail", "CompileFail"]:
                    counter += 1
                    self.logger.error(
                        "{}: {}.{} - {}".format(
                            counter,
                            result["ClassName"],
                            result["Method"],
                            result["Outcome"],
                        )
                    )
                    self.logger.error(f"\tMessage: {result['Message']}")
                    self.logger.error(f"\tStackTrace: {result['StackTrace']}")

        return test_results

    def _get_stats_from_result(self, result):
        stats = {"duration": result["RunTime"]}

        if result.get("ApexTestResults", None):
            for limit_name, details in APEX_LIMITS.items():
                limit_use = result["ApexTestResults"]["records"][0][limit_name]
                limit_allowed = details[
                    result["ApexTestResults"]["records"][0]["LimitContext"]
                ]
                stats[details["Label"]] = {"used": limit_use, "allowed": limit_allowed}

        return stats

    def _enqueue_test_run(self, class_ids):
        if isinstance(class_ids, dict):
            body = {
                "tests": [
                    {"classId": class_id, "testMethods": class_ids[class_id]}
                    for class_id in class_ids
                ]
            }
        else:
            body = {"classids": ",".join(class_ids)}

        return self.tooling._call_salesforce(
            method="POST", url=self.tooling.base_url + "runTestsAsynchronous", json=body
        ).json()

    def _run_task(self):
        result = self._get_test_classes()
        if result["totalSize"] == 0:
            return
        for test_class in result["records"]:
            self.classes_by_id[test_class["Id"]] = test_class["Name"]
            self.classes_by_name[test_class["Name"]] = test_class["Id"]
            self.results_by_class_name[test_class["Name"]] = {}
        self.logger.info("Queuing tests for execution...")

        self.counts = {
            "Pass": 0,
            "Fail": 0,
            "CompileFail": 0,
            "Skip": 0,
            "Retriable": 0,
        }
        self.job_id = self._enqueue_test_run(
            (str(id) for id in self.classes_by_id.keys())
        )

        self._wait_for_tests()
        self._get_test_results()

        # Did we get back retriable test results? Check our retry policy,
        # then enqueue new runs individually, until either (a) all retriable
        # tests succeed or (b) a test fails.
        able_to_retry = (self.counts["Retriable"] and self.options["retry_always"]) or (
            self.counts["Retriable"] and self.counts["Retriable"] == self.counts["Fail"]
        )
        if not able_to_retry:
            self.counts["Retriable"] = 0
        else:
            self._attempt_retries()

        test_results = self._process_test_results()
        self._write_output(test_results)

        if self.counts.get("Fail") or self.counts.get("CompileFail"):
            raise ApexTestException(
                "{} tests failed and {} tests failed compilation".format(
                    self.counts.get("Fail"), self.counts.get("CompileFail")
                )
            )

        if self.code_coverage_level:
            if self.options.get("namespace") not in self.org_config.installed_packages:
                self._check_code_coverage()
            else:
                self.logger.info(
                    "This org contains a managed installation; not checking code coverage."
                )
        else:
            self.logger.info(
                "No code coverage level specified; not checking code coverage."
            )

    def _check_code_coverage(self):
        result = self.tooling.query("SELECT PercentCovered FROM ApexOrgWideCoverage")
        coverage = result["records"][0]["PercentCovered"]
        if coverage < self.code_coverage_level:
            raise ApexTestException(
                f"Organization-wide code coverage of {coverage}% is below required level of {self.code_coverage_level}"
            )

        self.logger.info(
            f"Organization-wide code coverage of {coverage}% meets expectations."
        )

    def _attempt_retries(self):
        total_method_retries = sum(
            [len(test_list) for test_list in self.retry_details.values()]
        )
        self.logger.warning(
            "Retrying {} failed methods from {} test classes".format(
                total_method_retries, len(self.retry_details)
            )
        )
        self.counts["Fail"] = 0

        for class_id, test_list in self.retry_details.items():
            for each_test in test_list:
                self.logger.warning(
                    "Retrying {}.{}".format(self.classes_by_id[class_id], each_test)
                )
                self.job_id = self._enqueue_test_run({class_id: [each_test]})
                self._wait_for_tests()
                self._get_test_results(allow_retries=False)

        # If the retry failed, report the remaining failures.
        if self.counts["Fail"]:
            self.logger.error("Test retry failed.")

    def _wait_for_tests(self):
        self.poll_complete = False
        self.poll_interval_s = int(self.options.get("poll_interval", 1))
        self.poll_count = 0
        self._poll()

    def _poll_action(self):
        self.result = self.tooling.query_all(
            "SELECT Id, Status, ApexClassId FROM ApexTestQueueItem "
            + "WHERE ParentJobId = '{}'".format(self.job_id)
        )
        counts = {
            "Aborted": 0,
            "Completed": 0,
            "Failed": 0,
            "Holding": 0,
            "Preparing": 0,
            "Processing": 0,
            "Queued": 0,
        }
        processing_class_id = None
        total_test_count = self.result["totalSize"]
        for test_queue_item in self.result["records"]:
            counts[test_queue_item["Status"]] += 1
            if test_queue_item["Status"] == "Processing":
                processing_class_id = test_queue_item["ApexClassId"]
        processing_class = ""
        if counts["Processing"] == 1:
            processing_class = f" ({self.classes_by_id[processing_class_id]})"
        self.logger.info(
            "Completed: {}  Processing: {}{}  Queued: {}".format(
                counts["Completed"],
                counts["Processing"],
                processing_class,
                counts["Queued"],
            )
        )
        if (
            total_test_count
            == counts["Completed"] + counts["Failed"] + counts["Aborted"]
        ):
            self.logger.info("Apex tests completed")
            self.poll_complete = True

    def _write_output(self, test_results):
        junit_output = self.options["junit_output"]
        with io.open(junit_output, mode="w", encoding="utf-8") as f:
            f.write('<testsuite tests="{}">\n'.format(len(test_results)))
            for result in test_results:
                s = '  <testcase classname="{}" name="{}"'.format(
                    result["ClassName"], result["Method"]
                )
                if (
                    "Stats" in result
                    and result["Stats"]
                    and "duration" in result["Stats"]
                ):
                    s += ' time="{}"'.format(result["Stats"]["duration"])
                if result["Outcome"] in ["Fail", "CompileFail"]:
                    s += ">\n"
                    s += '    <failure type="failed" '
                    if result["Message"]:
                        s += 'message="{}"'.format(html.escape(result["Message"]))
                    s += ">"

                    if result["StackTrace"]:
                        s += "<![CDATA[{}]]>".format(html.escape(result["StackTrace"]))
                    s += "</failure>\n"
                    s += "  </testcase>\n"
                else:
                    s += " />\n"
                f.write(str(s))
            f.write("</testsuite>")

        json_output = self.options["json_output"]
        with io.open(json_output, mode="w", encoding="utf-8") as f:
            f.write(str(json.dumps(test_results, indent=4)))
