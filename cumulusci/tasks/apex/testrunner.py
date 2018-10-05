""" CumulusCI Tasks for running Apex Tests """

from builtins import str
from future import standard_library

standard_library.install_aliases()
import html
import io
import cgi
import json
import http.client

from simple_salesforce import SalesforceGeneralError

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import TaskOptionsError, ApexTestException
from cumulusci.core.utils import process_bool_arg, decode_to_unicode

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
            "description": (
                "Seconds to wait between polling for Apex test "
                + "results.  Defaults to 3"
            )
        },
        "retries": {"description": "Number of retries (default=10)"},
        "retry_interval": {
            "description": "Number of seconds to wait before the next retry (default=5),"
        },
        "retry_interval_add": {
            "description": "Number of seconds to add before each retry (default=5),"
        },
        "junit_output": {
            "description": "File name for JUnit output.  Defaults to test_results.xml"
        },
        "json_output": {
            "description": "File name for json output.  Defaults to test_results.json"
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

        self.options["retries"] = self.options.get("retries", 10)

        self.options["retry_interval"] = self.options.get("retry_interval", 5)

        self.options["retry_interval_add"] = self.options.get("retry_interval_add", 5)

        self.options["junit_output"] = self.options.get(
            "junit_output", "test_results.xml"
        )

        self.options["json_output"] = self.options.get(
            "json_output", "test_results.json"
        )

        self.options["managed"] = process_bool_arg(self.options.get("managed", False))

        self.counts = {}

    # pylint: disable=W0201
    def _init_class(self):
        self.classes_by_id = {}
        self.classes_by_name = {}
        self.job_id = None
        self.results_by_class_name = {}
        self.result = None

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

    def _get_test_results(self):
        result = self.tooling.query_all(TEST_RESULT_QUERY.format(self.job_id))
        self.counts = {"Pass": 0, "Fail": 0, "CompileFail": 0, "Skip": 0}
        for test_result in result["records"]:
            class_name = self.classes_by_id[test_result["ApexClassId"]]
            self.results_by_class_name[class_name][
                test_result["MethodName"]
            ] = test_result
            self.counts[test_result["Outcome"]] += 1
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
            "Pass: {}  Fail: {}  CompileFail: {}  Skip: {}".format(
                self.counts["Pass"],
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

    def _run_task(self):
        result = self._get_test_classes()
        if result["totalSize"] == 0:
            return
        for test_class in result["records"]:
            self.classes_by_id[test_class["Id"]] = test_class["Name"]
            self.classes_by_name[test_class["Name"]] = test_class["Id"]
            self.results_by_class_name[test_class["Name"]] = {}
        self.logger.info("Queuing tests for execution...")
        ids = list(self.classes_by_id.keys())
        result = self.tooling._call_salesforce(
            method="POST",
            url=self.tooling.base_url + "runTestsAsynchronous",
            json={"classids": ",".join(str(id) for id in ids)},
        )
        self.job_id = result.json()
        self._wait_for_tests()
        test_results = self._get_test_results()
        self._write_output(test_results)
        if self.counts.get("Fail") or self.counts.get("CompileFail"):
            raise ApexTestException(
                "{} tests failed and {} tests failed compilation".format(
                    self.counts.get("Fail"), self.counts.get("CompileFail")
                )
            )

    def _wait_for_tests(self):
        self._poll_interval_s = int(self.options.get("poll_interval", 1))
        self._poll()

    def _poll_action(self):
        self._retry()
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

    def _try(self):
        self.result = self.tooling.query_all(
            "SELECT Id, Status, ApexClassId FROM ApexTestQueueItem "
            + "WHERE ParentJobId = '{}'".format(self.job_id)
        )

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
