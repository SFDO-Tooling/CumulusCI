from cumulusci.tasks.bulkdata.step import (
    download_file,
    Operation,
    Status,
    Result,
    BulkJobTaskMixin,
    Step,
    DmlStep,
    QueryStep,
    BulkApiQueryStep,
    BulkApiDmlStep,
)
from cumulusci.core.exceptions import BulkDataException

import io
import responses
import unittest
from unittest import mock

BULK_BATCH_RESPONSE = """<root xmlns="http://ns">
<batch>
    <state>{first_state}</state>
    <stateMessage>{first_message}</stateMessage>
</batch>
<batch>
    <state>{second_state}</state>
    <stateMessage>{second_message}</stateMessage>
</batch>
</root>"""


class test_download_file(unittest.TestCase):
    @responses.activate
    def test_download_file(self):
        url = "https://example.com"
        bulk_mock = mock.Mock()
        bulk_mock.headers.return_value = {}

        responses.add(method="GET", url=url, body="TEST")
        with download_file(url, bulk_mock) as f:
            assert f.read() == "TEST"


class test_BulkDataJobTaskMixin(unittest.TestCase):
    @responses.activate
    def test_job_state_from_batches(self):
        mixin = BulkJobTaskMixin()
        mixin.bulk = mock.Mock()
        mixin.bulk.endpoint = "https://example.com"
        mixin.bulk.headers.return_value = {"HEADER": "test"}
        mixin._parse_job_state = mock.Mock()

        responses.add(
            "GET",
            "https://example.com/job/JOB/batch",
            adding_headers=mixin.bulk.headers.return_value,
            body="TEST",
        )
        assert (
            mixin._job_state_from_batches("JOB") == mixin._parse_job_state.return_value
        )
        mixin._parse_job_state.assert_called_once_with(b"TEST")

    def test_parse_job_state(self):
        mixin = BulkJobTaskMixin()
        mixin.bulk = mock.Mock()
        mixin.bulk.jobNS = "http://ns"

        assert mixin._parse_job_state(
            BULK_BATCH_RESPONSE.format(
                **{
                    "first_state": "Not Processed",
                    "first_message": "Test",
                    "second_state": "Completed",
                    "second_message": "",
                }
            )
        ) == ("Aborted", None)

        assert mixin._parse_job_state(
            BULK_BATCH_RESPONSE.format(
                **{
                    "first_state": "InProgress",
                    "first_message": "Test",
                    "second_state": "Completed",
                    "second_message": "",
                }
            )
        ) == ("InProgress", None)

        assert mixin._parse_job_state(
            BULK_BATCH_RESPONSE.format(
                **{
                    "first_state": "Failed",
                    "first_message": "Bad",
                    "second_state": "Failed",
                    "second_message": "Worse",
                }
            )
        ) == ("Failed", ["Bad", "Worse"])

        assert mixin._parse_job_state(
            BULK_BATCH_RESPONSE.format(
                **{
                    "first_state": "Completed",
                    "first_message": "Test",
                    "second_state": "Completed",
                    "second_message": "",
                }
            )
        ) == ("Completed", None)

        assert mixin._parse_job_state(
            '<root xmlns="http://ns">'
            "  <batch><state>Completed</state></batch>"
            "  <numberRecordsFailed>200</numberRecordsFailed>"
            "</root>"
        ) == ("CompletedWithFailures", ["Failures detected: 200"])

    @mock.patch("time.sleep")
    def test_wait_for_job(self, sleep_patch):
        mixin = BulkJobTaskMixin()

        mixin.bulk = mock.Mock()
        mixin.bulk.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        mixin._job_state_from_batches = mock.Mock(
            side_effect=[("InProgress", None), ("Completed", None)]
        )
        mixin.logger = mock.Mock()

        result = mixin._wait_for_job("750000000000000")
        mixin._job_state_from_batches.assert_has_calls(
            [mock.call("750000000000000"), mock.call("750000000000000")]
        )
        assert result == "Completed"

    def test_wait_for_job__failed(self):
        mixin = BulkJobTaskMixin()

        mixin.bulk = mock.Mock()
        mixin.bulk.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        mixin._job_state_from_batches = mock.Mock(
            return_value=("Failed", ["Test1", "Test2"])
        )
        mixin.logger = mock.Mock()

        result = mixin._wait_for_job("750000000000000")
        mixin._job_state_from_batches.assert_called_once_with("750000000000000")
        assert result == "Failed"

    def test_wait_for_job__logs_state_messages(self):
        mixin = BulkJobTaskMixin()

        mixin.bulk = mock.Mock()
        mixin.bulk.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        mixin._job_state_from_batches = mock.Mock(
            return_value=("Failed", ["Test1", "Test2"])
        )
        mixin.logger = mock.Mock()

        mixin._wait_for_job("750000000000000")
        mixin.logger.error.assert_any_call("Batch failure message: Test1")
        mixin.logger.error.assert_any_call("Batch failure message: Test2")


class test_Step(unittest.TestCase):
    def test_step(self):
        context = mock.Mock()
        s = Step("Contact", Operation.QUERY, {}, context)

        assert s.sobject == "Contact"
        assert s.operation is Operation.QUERY
        assert s.api_options == {}
        assert s.context == context
        assert s.sf == context.sf
        assert s.bulk == context.bulk
        assert s.logger == context.logger


class test_QueryStep(unittest.TestCase):
    def test_QueryStep(self):
        context = mock.Mock()
        step = QueryStep("Contact", {}, context, "SELECT Id FROM Contact")

        assert step.soql == "SELECT Id FROM Contact"
        assert step.operation is Operation.QUERY


class test_DmlStep(unittest.TestCase):
    context = mock.Mock()
    step = DmlStep("Contact", Operation.UPDATE, {}, context, ["FirstName", "LastName"])

    assert step.fields == ["FirstName", "LastName"]


class test_BulkApiQueryStep(unittest.TestCase):
    def test_query(self):
        context = mock.Mock()
        query = BulkApiQueryStep("Contact", {}, context, "SELECT Id FROM Contact")
        query._wait_for_job = mock.Mock()
        query._wait_for_job.return_value = ("Completed", None)

        query.query()

        assert query.status is Status.SUCCESS

        context.bulk.create_query_job.assert_called_once_with(
            "Contact", contentType="CSV"
        )
        context.bulk.query.assert_called_once_with(
            context.bulk.create_query_job.return_value, "SELECT Id FROM Contact"
        )
        query._wait_for_job.assert_called_once_with(
            context.bulk.create_query_job.return_value
        )
        context.bulk.close_job.assert_called_once_with(
            context.bulk.create_query_job.return_value
        )

    def test_query__failure(self):
        context = mock.Mock()
        query = BulkApiQueryStep("Contact", {}, context, "SELECT Id FROM Contact")
        query._wait_for_job = mock.Mock()
        query._wait_for_job.return_value = ("Failed", None)

        query.query()

        assert query.status is Status.FAILURE

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_get_results(self, download_mock):
        context = mock.Mock()
        context.bulk.endpoint = "https://test"
        context.bulk.create_query_job.return_value = "JOB"
        context.bulk.query.return_value = "BATCH"
        context.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        download_mock.return_value = io.StringIO(
            """Id
003000000000001
003000000000002
003000000000003"""
        )
        query = BulkApiQueryStep("Contact", {}, context, "SELECT Id FROM Contact")
        query._wait_for_job = mock.Mock()
        query._wait_for_job.return_value = ("Completed", None)
        query.query()

        results = list(query.get_results())

        context.bulk.get_query_batch_result_ids.assert_called_once_with(
            "BATCH", job_id="JOB"
        )
        download_mock.assert_called_once_with(
            f"https://test/job/JOB/batch/BATCH/result/RESULT", context.bulk
        )

        assert list(results) == [
            ["003000000000001"],
            ["003000000000002"],
            ["003000000000003"],
        ]

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_get_results__no_results(self, download_mock):
        context = mock.Mock()
        context.bulk.endpoint = "https://test"
        context.bulk.create_query_job.return_value = "JOB"
        context.bulk.query.return_value = "BATCH"
        context.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        download_mock.return_value = io.StringIO("Records not found for this query")
        query = BulkApiQueryStep("Contact", {}, context, "SELECT Id FROM Contact")
        query._wait_for_job = mock.Mock()
        query._wait_for_job.return_value = ("Completed", None)
        query.query()

        results = list(query.get_results())

        context.bulk.get_query_batch_result_ids.assert_called_once_with(
            "BATCH", job_id="JOB"
        )
        download_mock.assert_called_once_with(
            f"https://test/job/JOB/batch/BATCH/result/RESULT", context.bulk
        )

        assert list(results) == []


class test_BulkApiDmlStep(unittest.TestCase):
    def test_start(self):
        context = mock.Mock()
        context.bulk.create_job.return_value = "JOB"

        step = BulkApiDmlStep("Contact", Operation.INSERT, {}, context, ["LastName"])

        step.start()

        context.bulk.create_job.assert_called_once_with(
            "Contact", "insert", contentType="CSV", concurrency="Parallel"
        )
        assert step.job_id == "JOB"

    def test_end(self):
        context = mock.Mock()
        context.bulk.create_job.return_value = "JOB"

        step = BulkApiDmlStep("Contact", Operation.INSERT, {}, context, ["LastName"])
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = "Completed"
        step.job_id = "JOB"

        step.end()

        context.bulk.close_job.assert_called_once_with("JOB")
        step._wait_for_job.assert_called_once_with("JOB")
        assert step.status is Status.SUCCESS

    def test_end__failed(self):
        context = mock.Mock()
        context.bulk.create_job.return_value = "JOB"

        step = BulkApiDmlStep("Contact", Operation.INSERT, {}, context, ["LastName"])
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = "Failed"
        step.job_id = "JOB"

        step.end()

        context.bulk.close_job.assert_called_once_with("JOB")
        step._wait_for_job.assert_called_once_with("JOB")
        assert step.status is Status.FAILURE

    def test_load_records(self):
        context = mock.Mock()
        context.bulk.post_batch.side_effect = ["BATCH1", "BATCH2"]

        step = BulkApiDmlStep("Contact", Operation.INSERT, {}, context, ["LastName"])
        step._batch = mock.Mock()
        step._batch.return_value = [1, 2]
        step.job_id = "JOB"

        step.load_records(["RECORDS"])

        context.bulk.post_batch.assert_has_calls(
            [mock.call("JOB", 1), mock.call("JOB", 2)]
        )
        assert step.batch_ids == ["BATCH1", "BATCH2"]
        step._batch.assert_called_once_with(["RECORDS"])

    def test_batch(self):
        context = mock.Mock()

        step = BulkApiDmlStep(
            "Contact", Operation.INSERT, {"batch_size": 2}, context, ["LastName"]
        )

        results = list(step._batch(iter([["Test"], ["Test2"], ["Test3"]])))
        assert len(results) == 2
        assert list(results[0]) == ["LastName\r\n", "Test\r\n", "Test2\r\n"]
        assert list(results[1]) == ["LastName\r\n", "Test3\r\n"]

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_get_results(self, download_mock):
        context = mock.Mock()
        context.bulk.endpoint = "https://test"
        download_mock.side_effect = [
            io.StringIO(
                """id,success,created,error
003000000000001,true,true,
003000000000002,true,true,"""
            ),
            io.StringIO(
                """id,success,created,error
003000000000003,false,false,error"""
            ),
        ]

        step = BulkApiDmlStep("Contact", Operation.INSERT, {}, context, ["LastName"])
        step.job_id = "JOB"
        step.batch_ids = ["BATCH1", "BATCH2"]

        results = step.get_results()

        assert list(results) == [
            Result("003000000000001", True, None),
            Result("003000000000002", True, None),
            Result(None, False, "error"),
        ]
        download_mock.assert_has_calls(
            [
                mock.call("https://test/job/JOB/batch/BATCH1/result", context.bulk),
                mock.call("https://test/job/JOB/batch/BATCH2/result", context.bulk),
            ]
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_get_results__failure(self, download_mock):
        context = mock.Mock()
        context.bulk.endpoint = "https://test"
        download_mock.return_value.side_effect = Exception

        step = BulkApiDmlStep("Contact", Operation.INSERT, {}, context, ["LastName"])
        step.job_id = "JOB"
        step.batch_ids = ["BATCH1", "BATCH2"]

        with self.assertRaises(BulkDataException):
            list(step.get_results())

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_end_to_end(self, download_mock):
        context = mock.Mock()
        context.bulk.endpoint = "https://test"
        context.bulk.create_job.return_value = "JOB"
        context.bulk.post_batch.side_effect = ["BATCH1", "BATCH2"]
        download_mock.return_value = io.StringIO(
            """id,success,created,error
003000000000001,true,true,
003000000000002,true,true,
003000000000003,false,false,error"""
        )

        step = BulkApiDmlStep("Contact", Operation.INSERT, {}, context, ["LastName"])
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = "Completed"

        step.start()
        step.load_records(iter([["Test"], ["Test2"], ["Test3"]]))
        step.end()

        assert step.status is Status.SUCCESS
        results = step.get_results()

        assert list(results) == [
            Result("003000000000001", True, None),
            Result("003000000000002", True, None),
            Result(None, False, "error"),
        ]
