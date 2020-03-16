import io
import unittest
from unittest import mock

import responses

from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.step import (
    download_file,
    DataOperationType,
    DataOperationStatus,
    DataOperationResult,
    DataOperationJobResult,
    BulkJobMixin,
    BulkApiQueryOperation,
    BulkApiDmlOperation,
)


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


class TestDownloadFile(unittest.TestCase):
    @responses.activate
    def test_download_file(self):
        url = "https://example.com"
        bulk_mock = mock.Mock()
        bulk_mock.headers.return_value = {}

        responses.add(method="GET", url=url, body="TEST")
        with download_file(url, bulk_mock) as f:
            assert f.read() == "TEST"


class TestBulkDataJobTaskMixin(unittest.TestCase):
    @responses.activate
    def test_job_state_from_batches(self):
        mixin = BulkJobMixin()
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
        mixin = BulkJobMixin()
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
        ) == DataOperationJobResult(DataOperationStatus.ABORTED, [], 0, 0)

        assert mixin._parse_job_state(
            BULK_BATCH_RESPONSE.format(
                **{
                    "first_state": "InProgress",
                    "first_message": "Test",
                    "second_state": "Completed",
                    "second_message": "",
                }
            )
        ) == DataOperationJobResult(DataOperationStatus.IN_PROGRESS, [], 0, 0)

        assert mixin._parse_job_state(
            BULK_BATCH_RESPONSE.format(
                **{
                    "first_state": "Failed",
                    "first_message": "Bad",
                    "second_state": "Failed",
                    "second_message": "Worse",
                }
            )
        ) == DataOperationJobResult(
            DataOperationStatus.JOB_FAILURE, ["Bad", "Worse"], 0, 0
        )

        assert mixin._parse_job_state(
            BULK_BATCH_RESPONSE.format(
                **{
                    "first_state": "Completed",
                    "first_message": "Test",
                    "second_state": "Completed",
                    "second_message": "",
                }
            )
        ) == DataOperationJobResult(DataOperationStatus.SUCCESS, [], 0, 0)

        assert mixin._parse_job_state(
            '<root xmlns="http://ns">'
            "  <batch><state>Completed</state></batch>"
            "  <numberRecordsFailed>200</numberRecordsFailed>"
            "</root>"
        ) == DataOperationJobResult(DataOperationStatus.ROW_FAILURE, [], 0, 200)

        assert mixin._parse_job_state(
            '<root xmlns="http://ns">'
            "  <batch><state>Completed</state></batch>"
            "  <numberRecordsFailed>200</numberRecordsFailed>"
            "  <numberRecordsProcessed>10</numberRecordsProcessed>"
            "</root>"
        ) == DataOperationJobResult(DataOperationStatus.ROW_FAILURE, [], 10, 200)

    @mock.patch("time.sleep")
    def test_wait_for_job(self, sleep_patch):
        mixin = BulkJobMixin()

        mixin.bulk = mock.Mock()
        mixin.bulk.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        mixin._job_state_from_batches = mock.Mock(
            side_effect=[
                DataOperationJobResult(DataOperationStatus.IN_PROGRESS, [], 0, 0),
                DataOperationJobResult(DataOperationStatus.SUCCESS, [], 0, 0),
            ]
        )
        mixin.logger = mock.Mock()

        result = mixin._wait_for_job("750000000000000")
        mixin._job_state_from_batches.assert_has_calls(
            [mock.call("750000000000000"), mock.call("750000000000000")]
        )
        assert result.status is DataOperationStatus.SUCCESS

    def test_wait_for_job__failed(self):
        mixin = BulkJobMixin()

        mixin.bulk = mock.Mock()
        mixin.bulk.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        mixin._job_state_from_batches = mock.Mock(
            return_value=DataOperationJobResult(
                DataOperationStatus.JOB_FAILURE, ["Test1", "Test2"], 0, 0
            )
        )
        mixin.logger = mock.Mock()

        result = mixin._wait_for_job("750000000000000")
        mixin._job_state_from_batches.assert_called_once_with("750000000000000")
        assert result.status is DataOperationStatus.JOB_FAILURE

    def test_wait_for_job__logs_state_messages(self):
        mixin = BulkJobMixin()

        mixin.bulk = mock.Mock()
        mixin.bulk.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        mixin._job_state_from_batches = mock.Mock(
            return_value=DataOperationJobResult(
                DataOperationStatus.JOB_FAILURE, ["Test1", "Test2"], 0, 0
            )
        )
        mixin.logger = mock.Mock()

        mixin._wait_for_job("750000000000000")
        mixin.logger.error.assert_any_call("Batch failure message: Test1")
        mixin.logger.error.assert_any_call("Batch failure message: Test2")


class TestBulkApiQueryOperation(unittest.TestCase):
    def test_query(self):
        context = mock.Mock()
        query = BulkApiQueryOperation(
            sobject="Contact",
            api_options={},
            context=context,
            query="SELECT Id FROM Contact",
        )
        query._wait_for_job = mock.Mock()
        query._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        query.query()

        assert query.job_result.status is DataOperationStatus.SUCCESS

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

    def test_query__contextmanager(self):
        context = mock.Mock()
        query = BulkApiQueryOperation(
            sobject="Contact",
            api_options={},
            context=context,
            query="SELECT Id FROM Contact",
        )
        query._wait_for_job = mock.Mock()
        query._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        with query:
            assert query.job_result.status is DataOperationStatus.SUCCESS

    def test_query__failure(self):
        context = mock.Mock()
        query = BulkApiQueryOperation(
            sobject="Contact",
            api_options={},
            context=context,
            query="SELECT Id FROM Contact",
        )
        query._wait_for_job = mock.Mock()
        query._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.JOB_FAILURE, [], 0, 0
        )

        query.query()

        assert query.job_result.status is DataOperationStatus.JOB_FAILURE

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
        query = BulkApiQueryOperation(
            sobject="Contact",
            api_options={},
            context=context,
            query="SELECT Id FROM Contact",
        )
        query._wait_for_job = mock.Mock()
        query._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )
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
        query = BulkApiQueryOperation(
            sobject="Contact",
            api_options={},
            context=context,
            query="SELECT Id FROM Contact",
        )
        query._wait_for_job = mock.Mock()
        query._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )
        query.query()

        results = list(query.get_results())

        context.bulk.get_query_batch_result_ids.assert_called_once_with(
            "BATCH", job_id="JOB"
        )
        download_mock.assert_called_once_with(
            f"https://test/job/JOB/batch/BATCH/result/RESULT", context.bulk
        )

        assert list(results) == []


class TestBulkApiDmlOperation(unittest.TestCase):
    def test_start(self):
        context = mock.Mock()
        context.bulk.create_job.return_value = "JOB"

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=context,
            fields=["LastName"],
        )

        step.start()

        context.bulk.create_job.assert_called_once_with(
            "Contact", "insert", contentType="CSV", concurrency="Parallel"
        )
        assert step.job_id == "JOB"

    def test_end(self):
        context = mock.Mock()
        context.bulk.create_job.return_value = "JOB"

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=context,
            fields=["LastName"],
        )
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )
        step.job_id = "JOB"

        step.end()

        context.bulk.close_job.assert_called_once_with("JOB")
        step._wait_for_job.assert_called_once_with("JOB")
        assert step.job_result.status is DataOperationStatus.SUCCESS

    def test_end__failed(self):
        context = mock.Mock()
        context.bulk.create_job.return_value = "JOB"

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=context,
            fields=["LastName"],
        )
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.JOB_FAILURE, [], 0, 0
        )
        step.job_id = "JOB"

        step.end()

        context.bulk.close_job.assert_called_once_with("JOB")
        step._wait_for_job.assert_called_once_with("JOB")
        assert step.job_result.status is DataOperationStatus.JOB_FAILURE

    def test_contextmanager(self):
        context = mock.Mock()
        context.bulk.create_job.return_value = "JOB"

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=context,
            fields=["LastName"],
        )
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )
        step.job_id = "JOB"

        with step:
            pass

        context.bulk.create_job.assert_called_once_with(
            "Contact", "insert", contentType="CSV", concurrency="Parallel"
        )
        assert step.job_id == "JOB"

        context.bulk.close_job.assert_called_once_with("JOB")
        step._wait_for_job.assert_called_once_with("JOB")
        assert step.job_result.status is DataOperationStatus.SUCCESS

    def test_load_records(self):
        context = mock.Mock()
        context.bulk.post_batch.side_effect = ["BATCH1", "BATCH2"]

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=context,
            fields=["LastName"],
        )
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

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={"batch_size": 2},
            context=context,
            fields=["LastName"],
        )

        results = list(step._batch(iter([["Test"], ["Test2"], ["Test3"]])))
        assert len(results) == 2
        assert list(results[0]) == [
            "LastName\r\n".encode("utf-8"),
            "Test\r\n".encode("utf-8"),
            "Test2\r\n".encode("utf-8"),
        ]
        assert list(results[1]) == [
            "LastName\r\n".encode("utf-8"),
            "Test3\r\n".encode("utf-8"),
        ]

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

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=context,
            fields=["LastName"],
        )
        step.job_id = "JOB"
        step.batch_ids = ["BATCH1", "BATCH2"]

        results = step.get_results()

        assert list(results) == [
            DataOperationResult("003000000000001", True, None),
            DataOperationResult("003000000000002", True, None),
            DataOperationResult(None, False, "error"),
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

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=context,
            fields=["LastName"],
        )
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

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=context,
            fields=["LastName"],
        )
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        step.start()
        step.load_records(iter([["Test"], ["Test2"], ["Test3"]]))
        step.end()

        assert step.job_result.status is DataOperationStatus.SUCCESS
        results = step.get_results()

        assert list(results) == [
            DataOperationResult("003000000000001", True, None),
            DataOperationResult("003000000000002", True, None),
            DataOperationResult(None, False, "error"),
        ]
