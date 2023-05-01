import csv
import os.path
from unittest import mock

from cumulusci.tasks.push.pushfails import ReportPushFailures
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.utils import temporary_dir


def error_record(gack=False, ErrorTitle="Unexpected Error"):  # type: (bool) -> dict
    """a record that looks like the object returned from the sobject api query we use"""
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


class TestPushFailureTask:
    def test_run_task(
        self,
    ):
        task = create_task(
            ReportPushFailures,
            options={"request_id": "123", "ignore_errors": "IgnoreMe"},
        )

        def _init_class():
            task.sf = mock.Mock()
            task.sf.query_all.side_effect = [
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

        task._init_class = _init_class
        with temporary_dir():
            task()
            assert 2 == task.sf.query_all.call_count
            assert os.path.isfile(task.result), "the result file does not exist"
            with open(task.result, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert len(rows) == 2
            assert rows[1]["Stacktrace Id"] == "-4532"

    def test_run_task__no_results(self):
        task = create_task(ReportPushFailures, options={"request_id": "123"})

        def _init_class():
            task.sf = mock.Mock()
            task.sf.query_all.return_value = {
                "totalSize": 0,
                "records": [],
                "done": True,
            }

        task._init_class = _init_class
        task()
        assert not os.path.isfile(task.options["result_file"])
