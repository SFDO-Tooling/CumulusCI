import csv
import mock
import os.path
import unittest

from cumulusci.core.config import (
    BaseGlobalConfig,
    BaseProjectConfig,
    TaskConfig,
    OrgConfig,
)
from cumulusci.utils import temporary_dir
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.push.pushfails import ReportPushFailures


def error_record(gack=False, ErrorTitle="Unexpected Error"):  # type: (bool) -> dict
    """ a record that looks like the object returned from the sobject api query we use """
    return {
        "attributes": {"type": "job"},
        "SubscriberOrganizationKey": "00Dxxx000000001",
        "PackagePushErrors": {
            "totalSize": 1,
            "records": [
                {
                    "attributes": {"type": "error"},
                    "ErrorDetails": "None to be had",
                    "ErrorMessage": "There was an error number: 123456-765432 (-4532)"
                    if gack
                    else "Who knows?",
                    "ErrorSeverity": "Severe",
                    "ErrorTitle": ErrorTitle,
                    "ErrorType": "Error",
                }
            ],
        },
    }


class TestPushFailureTask(unittest.TestCase):
    def test_run_task(self,):
        task = create_task(
            ReportPushFailures,
            options={"request_id": "123", "ignore_errors": "IgnoreMe"},
        )
        task.sf = mock.Mock()
        task.sf.query.side_effect = [
            {
                "done": True,
                "totalSize": 2,
                "records": [
                    error_record(ErrorTitle="IgnoreMe"),
                    error_record(gack=True),
                    {
                        "attributes": {"type": "job"},
                        "SubscriberOrganizationKey": "00Dxxx000000001",
                    },
                ],
            },
            {
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "OrgKey": "00Dxxx000000001",
                        "OrgName": "Test Org",
                        "OrgType": "Sandbox",
                        "OrgStatus": "Demo",
                        "InstanceName": "CSxx",
                    }
                ],
            },
        ]
        with temporary_dir():
            task()
            self.assertEqual(2, task.sf.query.call_count)
            self.assertTrue(
                os.path.isfile(task.result), "the result file does not exist"
            )
            with open(task.result, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["Stacktrace Id"], "-4532")

    def test_run_task__no_results(self):
        task = create_task(ReportPushFailures, options={"request_id": "123"})
        task.sf = mock.Mock()
        task.sf.query.return_value = {"totalSize": 0, "records": [], "done": True}
        task()
        self.assertFalse(os.path.isfile(task.options["result_file"]))
