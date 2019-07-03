import time
import mock
import json
import tempfile
import unittest
from pathlib import Path

from cumulusci.tasks.robotframework import robotperflistener


class TestRobotPerfListener(unittest.TestCase):
    def start_listener(self, verbosity=0):
        """Helper function that does setup to the point of starting a test"""
        task = mock.MagicMock()
        self.rpl = robotperflistener.RobotPerfListener(task, verbosity)
        self.rpl.start_suite("fake_suite")
        self.rpl.start_test("fake_test")
        return self.rpl

    def finish_listener(self):
        """Helper function that does teardown and returns json"""
        self.rpl.end_test("fake_test")
        self.rpl.end_suite("fake_suite")
        with tempfile.TemporaryDirectory() as temporary:
            tempdir = Path(temporary)
            self.rpl.output_file(tempdir / "junk.xml")
            self.rpl.close()
            return json.load(open(tempdir / "perf.json"))

    def test_lifecyle(self):
        """Test the basics"""
        self.start_listener()
        json = self.finish_listener()
        assert json

    def test_metric_totalling(self):
        rpl = self.start_listener()
        rpl.create_aggregate_metric("my summation", "sum")
        rpl.store_metric_value("my summation", 5)
        rpl.store_metric_value("my summation", 15)
        rpl.store_metric_value("my summation", 25)
        json = self.finish_listener()
        assert json["fake_suite"]["fake_test"]["totals"]["my summation"] == 45

    def test_metric_averaging(self):
        rpl = self.start_listener()
        rpl.create_aggregate_metric("my mean", "average")
        rpl.store_metric_value("my mean", 7)
        rpl.store_metric_value("my mean", 10)
        rpl.store_metric_value("my mean", 13)
        json = self.finish_listener()
        assert json["fake_suite"]["fake_test"]["totals"]["my mean"] == 10

    def test_metric_duration(self):
        rpl = self.start_listener()
        rpl.create_duration_metric("my duration")
        time.sleep(0.25)
        rpl.end_duration_metric("my duration")
        json = self.finish_listener()
        assert json["fake_suite"]["fake_test"]["totals"]["my duration"] > 0.25

    def test_api_summarization(self):
        rpl = self.start_listener()
        for row in API_SAMPLE_DATA:
            rpl.report(row)
        json = self.finish_listener()
        assert json["fake_suite"]["fake_test"]["totals"] == API_SAMPLE_TOTALS

    def test_more_verbosity(self):
        rpl = self.start_listener(verbosity=2)
        for row in API_SAMPLE_DATA:
            rpl.report(row)
        json = self.finish_listener()
        assert json["fake_suite"]["fake_test"]["totals"] == API_SAMPLE_TOTALS


API_SAMPLE_DATA = [
    {
        "_meta": {
            "url": "https://agility-velocity-4937-dev-ed.cs93.my.salesforce.com//services/data/v46.0/sobjects/Contact/",
            "method": "POST",
        },
        "rest-api-totalTime": 228,
        "db-conn-wait-totalTime": 0,
        "db-exec-totalTime": 24,
        "cache-caas-totalTime": 0,
        "http-request-totalTime": 235,
        "request-tracing-enable-totalTime": 0,
        "udd-bulk-dml-totalTime": 147,
        "rest-api-totalCalls": 1,
        "db-conn-wait-totalCalls": 5,
        "db-exec-totalCalls": 33,
        "cache-caas-totalCalls": 47,
        "http-request-totalCalls": 1,
        "request-tracing-enable-totalCalls": 3,
        "udd-bulk-dml-totalCalls": 2,
    },
    {
        "_meta": {
            "url": "https://agility-velocity-4937-dev-ed.cs93.my.salesforce.com/services/data/v46.0/sobjects/Contact/0034F00000OoaGLQAZ",
            "method": "GET",
        },
        "rest-api-totalTime": 58,
        "db-conn-wait-totalTime": 0,
        "db-exec-totalTime": 31,
        "cache-caas-totalTime": 0,
        "http-request-totalTime": 62,
        "request-tracing-enable-totalTime": 0,
        "rest-api-totalCalls": 1,
        "db-conn-wait-totalCalls": 3,
        "db-exec-totalCalls": 11,
        "cache-caas-totalCalls": 26,
        "http-request-totalCalls": 1,
        "request-tracing-enable-totalCalls": 3,
    },
    {
        "_meta": {
            "url": "https://agility-velocity-4937-dev-ed.cs93.my.salesforce.com/services/data/v46.0/sobjects/Contact/0034F00000OoaGLQAZ",
            "method": "DELETE",
        },
        "db-conn-wait-totalTime": 0,
        "rest-api-totalTime": 1244,
        "db-exec-totalTime": 13,
        "cache-caas-totalTime": 0,
        "http-request-totalTime": 1250,
        "request-tracing-enable-totalTime": 0,
        "udd-bulk-dml-totalTime": 1207,
        "db-conn-wait-totalCalls": 5,
        "rest-api-totalCalls": 1,
        "db-exec-totalCalls": 16,
        "cache-caas-totalCalls": 25,
        "http-request-totalCalls": 1,
        "request-tracing-enable-totalCalls": 3,
        "udd-bulk-dml-totalCalls": 1,
    },
    {
        "_meta": {
            "url": "https://agility-velocity-4937-dev-ed.cs93.my.salesforce.com//services/data/v46.0/query/?q=Select+Id+from+Contact+WHERE+Id+%3D+%270034F00000OoaGLQAZ%27",
            "method": "GET",
        },
        "rest-api-totalTime": 29,
        "db-conn-wait-totalTime": 0,
        "soql-totalTime": 14,
        "db-exec-totalTime": 5,
        "cache-caas-totalTime": 0,
        "http-request-totalTime": 31,
        "request-tracing-enable-totalTime": 0,
        "rest-api-totalCalls": 1,
        "db-conn-wait-totalCalls": 2,
        "soql-totalCalls": 1,
        "db-exec-totalCalls": 8,
        "cache-caas-totalCalls": 23,
        "http-request-totalCalls": 1,
        "request-tracing-enable-totalCalls": 3,
    },
]

# These numbers have been spot-checked with a spreadsheet
API_SAMPLE_TOTALS = {
    "cache-caas-totalCalls-avg": 30.25,
    "cache-caas-totalCalls-sum": 121.0,
    "cache-caas-totalTime-avg": 0.0,
    "cache-caas-totalTime-sum": 0.0,
    "db-conn-wait-totalCalls-avg": 3.75,
    "db-conn-wait-totalCalls-sum": 15.0,
    "db-conn-wait-totalTime-avg": 0.0,
    "db-conn-wait-totalTime-sum": 0.0,
    "db-exec-totalCalls-avg": 17.0,  # checked
    "db-exec-totalCalls-sum": 68.0,  # checked
    "db-exec-totalTime-avg": 18.25,  # checked
    "db-exec-totalTime-sum": 73.0,  # checked
    "http-request-totalCalls-avg": 1.0,
    "http-request-totalCalls-sum": 4.0,
    "http-request-totalTime-avg": 394.5,
    "http-request-totalTime-sum": 1578.0,
    "request-tracing-enable-totalCalls-avg": 3.0,
    "request-tracing-enable-totalCalls-sum": 12.0,
    "request-tracing-enable-totalTime-avg": 0.0,
    "request-tracing-enable-totalTime-sum": 0.0,
    "rest-api-totalCalls-avg": 1.0,
    "rest-api-totalCalls-sum": 4.0,
    "rest-api-totalTime-avg": 389.75,
    "rest-api-totalTime-sum": 1559.0,
    "soql-totalCalls-avg": 1.0,
    "soql-totalCalls-sum": 1.0,
    "soql-totalTime-avg": 14.0,
    "soql-totalTime-sum": 14.0,
    "udd-bulk-dml-totalCalls-avg": 1.5,
    "udd-bulk-dml-totalCalls-sum": 3.0,
    "udd-bulk-dml-totalTime-avg": 677.0,
    "udd-bulk-dml-totalTime-sum": 1354.0,
}
