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
from cumulusci.tasks.salesforce.tests.util import SalesforceTaskTestCase
from cumulusci.tasks.push.pushfails import ReportPushFailures


def error_record(gack=False):  # type: (bool) -> dict
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
                    "ErrorTitle": "Unexpected Error",
                    "ErrorType": "Error",
                }
            ],
        },
    }


class TestPushFailureTask(SalesforceTaskTestCase):
    task_class = ReportPushFailures

    def test_run_task(self,):
        task = self.create_task(options={"request_id": "123"})
        task.sf = mock.Mock()
        task.sf.query.return_value = {
            "done": True,
            "totalSize": 2,
            "records": [
                error_record(),
                error_record(True),
                {
                    "attributes": {"type": "job"},
                    "SubscriberOrganizationKey": "00Dxxx000000001",
                },
            ],
        }
        with temporary_dir():
            task()
            task.sf.query.assert_called_once()
            self.assertTrue(
                os.path.isfile(task.result), "the result file does not exist"
            )
            with open(task.result, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[1]["Stacktrace Id"], "-4532")
