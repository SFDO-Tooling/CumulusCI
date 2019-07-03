import unittest

from cumulusci.robotframework import utils


class TestRobotUtils(unittest.TestCase):
    def test_to_dict(self):
        converter = utils.PerfJSONConverter(SAMPLE_PERF_JSON)
        d = converter.to_dict()
        self.assertIsInstance(d, dict)
        self.assertTrue(d)
        d = converter.to_dict(include_raw=True)
        self.assertIsInstance(d, dict)
        self.assertTrue(d["_raw"])

    def test_to_log_message(self):
        converter = utils.PerfJSONConverter(SAMPLE_PERF_JSON)
        log_message = converter.to_log_message()
        self.assertIsInstance(log_message, str)
        self.assertTrue(log_message)


SAMPLE_PERF_JSON = """
        {
            "version": "1.0.0",
            "callTree": {
              "name": "http-request",
              "attachment": {},
              "startTime": 26962742,
              "endTime": 26963313,
              "ownTime": 0,
              "childTime": 570,
              "totalTime": 571,
              "children": [
                {
                  "name": "rest-api",
                  "attachment": {
                    "URI": "/v46.0/sobjects/Contact/",
                    "resource-class": "common.api.rest.SObjectResource",
                    "resource-method": "POST"
                  },
                  "startTime": 26962743,
                  "endTime": 26963313,
                  "ownTime": 20,
                  "childTime": 549,
                  "totalTime": 569,
                  "children": []
                }
              ]
            },
            "summary": [
              {
                "metrics": "rest-api",
                "totalTime": 569,
                "totalCalls": 1
              },
              {
                "metrics": "db-conn-wait",
                "totalTime": 0,
                "totalCalls": 3
              },
              {
                "metrics": "db-exec",
                "totalTime": 6,
                "totalCalls": 19
              },
              {
                "metrics": "cache-caas",
                "totalTime": 0,
                "totalCalls": 24
              },
              {
                "metrics": "http-request",
                "totalTime": 571,
                "totalCalls": 1
              },
              {
                "metrics": "request-tracing-enable",
                "totalTime": 0,
                "totalCalls": 3
              },
              {
                "metrics": "udd-bulk-dml",
                "totalTime": 528,
                "totalCalls": 2
              }
            ]
          }
"""
