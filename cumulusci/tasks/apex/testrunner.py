""" CumulusCI Tasks for running Apex Tests """

from builtins import str
from future import standard_library

standard_library.install_aliases()
import html
import io
import json
import re

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import TaskOptionsError, ApexTestException
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
    """ Task to run Apex tests with the Tooling API and report results """

    api_version = "38.0"
    name = "RunApexTests"
    task_options = {
        "test_name_match": {
            "description": (
                "Query to find Apex test classes to run "
                + '("%" is wildcard).  Defaults to '
                + "project__test__name_match"
            ),
            "required": True,
        },
        "test_name_exclude": {
            "description": (
                "Query to find Apex test classes to exclude "
                + '("%" is wildcard).  Defaults to '
                + "project__test__name_exclude"
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

        self.counts = {}

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

    def _is_retriable_failure(self, test_result):
        return test_result["Outcome"] == "Fail" and any(
            [
                reg.search(test_result["Message"] or "")
                or reg.search(test_result["StackTrace"] or "")
                for reg in self.options["retry_failures"]
            ]
        )

    def _get_test_results(self, allow_retries=True):
        result = self.tooling.query_all(TEST_RESULT_QUERY.format(self.job_id))

        if allow_retries:
            self.retry_details = {}

        for test_result in result["records"]:
            class_name = self.classes_by_id[test_result["ApexClassId"]]
            self.results_by_class_name[class_name][
                test_result["MethodName"]
            ] = test_result
            self.counts[test_result["Outcome"]] += 1

            # Determine whether this failure is retriable.
            if allow_retries and self._is_retriable_failure(test_result):
                self.counts["Retriable"] += 1
                self.retry_details.setdefault(test_result["ApexClassId"], []).append(
                    test_result["MethodName"]
                )

    def _process_test_results(self):
        test_results = []
        class_names = list(self.results_by_class_name.keys())
        class_names.sort()
        for class_name in class_names:
            message = "Class: {}".format(class_name)
            self.logger.info(message)
            method_names = list(self.results_by_class_name[class_name].keys())
            method_names.sort()
            for method_name in method_names:
                result = self.results_by_class_name[class_name][method_name]
                message = "\t{}: {}".format(result["Outcome"], result["MethodName"])
                duration = result["RunTime"]
                result["stats"] = self._get_stats_from_result(result)
                if duration:
                    message += " ({}s)".format(duration)
                self.logger.info(message)
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
                    self.logger.info("\tMessage: {}".format(result["Message"]))
                    self.logger.info("\tStackTrace: {}".format(result["StackTrace"]))
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
                    self.logger.error("\tMessage: {}".format(result["Message"]))
                    self.logger.error("\tStackTrace: {}".format(result["StackTrace"]))

        return test_results

    def _get_stats_from_result(self, result):
        stats = {"duration": result["RunTime"]}

        if result["ApexTestResults"]:
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

        if self.counts["Retriable"]:
            # All our retries succeeded. Clear the failure counter.
            self.counts["Fail"] = 0

        test_results = self._process_test_results()
        self._write_output(test_results)

        if self.counts.get("Fail") or self.counts.get("CompileFail"):
            raise ApexTestException(
                "{} tests failed and {} tests failed compilation".format(
                    self.counts.get("Fail"), self.counts.get("CompileFail")
                )
            )

    def _attempt_retries(self):
        self.logger.warning(
            "Retrying failed methods from {} test classes".format(
                len(self.retry_details)
            )
        )
        # Save the pre-retry status counts. If the retries fail, we'll report the originals.
        original_counts = self.counts.copy()
        for class_id, test_list in self.retry_details.items():
            for each_test in test_list:
                self.logger.warning(
                    "Retrying {}.{}".format(self.classes_by_id[class_id], each_test)
                )
                self.job_id = self._enqueue_test_run({class_id: [each_test]})
                self._wait_for_tests()
                self._get_test_results(allow_retries=False)
                # If the retry failed, stop and count all retried tests
                # under their original failures.
                if self.counts["Fail"] > original_counts["Fail"]:
                    self.logger.error("Test retry failed.")
                    # Reset counts to avoid double-counting retried failures
                    self.counts = original_counts
                    self.counts["Retriable"] = 0
                    return

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
        for test_queue_item in self.result["records"]:
            counts[test_queue_item["Status"]] += 1
        self.logger.info(
            "Completed: {}  Processing: {}  Queued: {}".format(
                counts["Completed"], counts["Processing"], counts["Queued"]
            )
        )
        if counts["Queued"] == 0 and counts["Processing"] == 0:
            self.logger.info("Apex tests completed")
            self.poll_complete = True

    def _write_output(self, test_results):
        junit_output = self.options["junit_output"]
        with io.open(junit_output, mode="w", encoding="utf-8") as f:
            f.write(u'<testsuite tests="{}">\n'.format(len(test_results)))
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
            f.write(u"</testsuite>")

        json_output = self.options["json_output"]
        with io.open(json_output, mode="w", encoding="utf-8") as f:
            f.write(str(json.dumps(test_results, indent=4)))
