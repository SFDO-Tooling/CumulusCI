from unittest import mock

import pytest

from cumulusci.robotframework.Performance import Performance
from cumulusci.robotframework.SalesforceAPI import SalesforceAPI


class TestKeyword_elapsed_time_for_last_record:
    def test_elapsed_time_for_last_record__query_empty(self):
        perflib = Performance()
        records = {"records": []}

        with mock.patch.object(perflib, "_salesforce_api", SalesforceAPI()):
            with mock.patch.object(SalesforceAPI, "cumulusci") as cumulusci:
                cumulusci.sf.query_all.return_value = records
                with pytest.raises(Exception) as e:
                    perflib.elapsed_time_for_last_record("FOO", "Bar", "Baz", "Baz")
                assert "Matching record not found" in str(e.value)

    def test_elapsed_time_for_last_record__query_returns_result(self):
        perflib = Performance()
        records = {
            "records": [
                {
                    "CreatedDate": "2020-12-29T10:00:01.000+0000",
                    "CompletedDate": "2020-12-29T10:00:04.000+0000",
                }
            ],
        }

        with mock.patch.object(perflib, "_salesforce_api", SalesforceAPI()):
            with mock.patch.object(SalesforceAPI, "cumulusci") as cumulusci:
                cumulusci.sf.query_all.return_value = records
                elapsed = perflib.elapsed_time_for_last_record(
                    "AsyncApexJob", "CreatedDate", "CompletedDate", "CompletedDate"
                )
                assert elapsed == 3
