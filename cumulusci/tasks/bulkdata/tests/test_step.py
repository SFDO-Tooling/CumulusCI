import io
import json
from itertools import tee
from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.bulkdata.select_utils import SelectStrategy
from cumulusci.tasks.bulkdata.step import (
    HIGH_PRIORITY_VALUE,
    LOW_PRIORITY_VALUE,
    BulkApiDmlOperation,
    BulkApiQueryOperation,
    BulkJobMixin,
    DataApi,
    DataOperationJobResult,
    DataOperationResult,
    DataOperationStatus,
    DataOperationType,
    RestApiDmlOperation,
    RestApiQueryOperation,
    assign_weights,
    download_file,
    extract_flattened_headers,
    flatten_record,
    get_dml_operation,
    get_query_operation,
)
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.tests.util import CURRENT_SF_API_VERSION, mock_describe_calls

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


class TestDownloadFile:
    @responses.activate
    def test_download_file(self):
        url = "https://example.com"
        bulk_mock = mock.Mock()
        bulk_mock.headers.return_value = {}

        responses.add(method="GET", url=url, body=b"TEST\xe2\x80\x94")
        with download_file(url, bulk_mock) as f:
            # make sure it was decoded as utf-8
            assert f.read() == "TEST\u2014"


class TestBulkDataJobTaskMixin:
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
            "  <batch>"
            "    <state>Completed</state>"
            "    <numberRecordsFailed>200</numberRecordsFailed>"
            "    </batch>"
            "  <batch>"
            "    <state>Completed</state>"
            "    <numberRecordsFailed>200</numberRecordsFailed>"
            "    </batch>"
            "</root>"
        ) == DataOperationJobResult(
            DataOperationStatus.ROW_FAILURE, [], 0, 400
        ), "Multiple batches in single job"

        assert mixin._parse_job_state(
            '<root xmlns="http://ns">'
            "  <batch>"
            "    <state>Completed</state>"
            "    <numberRecordsFailed>200</numberRecordsFailed>"
            "    </batch>"
            "</root>"
        ) == DataOperationJobResult(
            DataOperationStatus.ROW_FAILURE, [], 0, 200
        ), "Single batch"

        assert mixin._parse_job_state(
            '<root xmlns="http://ns">'
            "  <batch>"
            "    <state>Completed</state>"
            "    <numberRecordsFailed>200</numberRecordsFailed>"
            "    <numberRecordsProcessed>10</numberRecordsProcessed>"
            "    </batch>"
            "  <batch>"
            "    <state>Completed</state>"
            "    <numberRecordsFailed>200</numberRecordsFailed>"
            "    <numberRecordsProcessed>10</numberRecordsProcessed>"
            "    </batch>"
            "</root>"
        ) == DataOperationJobResult(
            DataOperationStatus.ROW_FAILURE, [], 20, 400
        ), "Multiple batches in single job"

        assert mixin._parse_job_state(
            '<root xmlns="http://ns">'
            "  <batch><state>Completed</state></batch>"
            "  <numberRecordsFailed>200</numberRecordsFailed>"
            "  <numberRecordsProcessed>10</numberRecordsProcessed>"
            "</root>"
        ) == DataOperationJobResult(
            DataOperationStatus.ROW_FAILURE, [], 10, 200
        ), "Single batch"

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


class TestBulkApiQueryOperation:
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
            "https://test/job/JOB/batch/BATCH/result/RESULT", context.bulk
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
            "https://test/job/JOB/batch/BATCH/result/RESULT", context.bulk
        )

        assert list(results) == []


class TestBulkApiDmlOperation:
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
            "Contact",
            "insert",
            contentType="CSV",
            concurrency="Parallel",
            external_id_name=None,
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
            "Contact",
            "insert",
            contentType="CSV",
            concurrency="Parallel",
            external_id_name=None,
        )
        assert step.job_id == "JOB"

        context.bulk.close_job.assert_called_once_with("JOB")
        step._wait_for_job.assert_called_once_with("JOB")
        assert step.job_result.status is DataOperationStatus.SUCCESS

    def test_serialize_csv_record(self):
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={"batch_size": 2},
            context=context,
            fields=["Id", "FirstName", "LastName"],
        )

        serialized = step._serialize_csv_record(step.fields)
        assert serialized == b'"Id","FirstName","LastName"\r\n'

        record = ["1", "Bob", "Ross"]
        serialized = step._serialize_csv_record(record)
        assert serialized == b'"1","Bob","Ross"\r\n'

        record = ["col1", "multiline\ncol2"]
        serialized = step._serialize_csv_record(record)
        assert serialized == b'"col1","multiline\ncol2"\r\n'

    def test_get_prev_record_values(self):
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["LastName"],
        )
        results = [
            [{"LastName": "Test1", "Id": "Id1"}, {"LastName": "Test2", "Id": "Id2"}]
        ]
        expected_record_values = [["Test1", "Id1"], ["Test2", "Id2"]]
        expected_relevant_fields = ("Id", "LastName")
        step.bulk.create_query_job = mock.Mock()
        step.bulk.create_query_job.return_value = "JOB_ID"
        step.bulk.query = mock.Mock()
        step.bulk.query.return_value = "BATCH_ID"
        step.bulk.get_all_results_for_query_batch = mock.Mock()
        step.bulk.get_all_results_for_query_batch.return_value = results

        records = iter([["Test1"], ["Test2"], ["Test3"]])
        with mock.patch("json.load", side_effect=lambda result: result), mock.patch(
            "salesforce_bulk.util.IteratorBytesIO", side_effect=lambda result: result
        ):
            prev_record_values, relevant_fields = step.get_prev_record_values(records)

        assert sorted(map(sorted, prev_record_values)) == sorted(
            map(sorted, expected_record_values)
        )
        assert set(relevant_fields) == set(expected_relevant_fields)
        step.bulk.create_query_job.assert_called_once_with(
            "Contact", contentType="JSON"
        )
        step.bulk.get_all_results_for_query_batch.assert_called_once_with("BATCH_ID")

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_standard_strategy_success(self, download_mock):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
            content_type="JSON",
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content with a single record
        download_mock.return_value = io.StringIO('[{"Id":"003000000000001"}]')

        # Mock the _wait_for_job method to simulate a successful job
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        # Prepare input records
        records = iter([["Test1"], ["Test2"], ["Test3"]])

        # Execute the select_records operation
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 3
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_zero_load_records(self, download_mock):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
            content_type="JSON",
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content with a single record
        download_mock.return_value = io.StringIO('[{"Id":"003000000000001"}]')

        # Mock the _wait_for_job method to simulate a successful job
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        # Prepare input records
        records = iter([])

        # Execute the select_records operation
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 0  # Expect 0 results (no records to process)

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_standard_strategy_failure__no_records(self, download_mock):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content indicating no records found
        download_mock.return_value = io.StringIO("[]")

        # Mock the _wait_for_job method to simulate a successful job
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        # Prepare input records
        records = iter([["Test1"], ["Test2"], ["Test3"]])

        # Execute the select_records operation
        step.start()
        step.select_records(records)
        step.end()

        # Get the job result and assert its properties for failure scenario
        job_result = step.job_result
        assert job_result.status == DataOperationStatus.JOB_FAILURE
        assert (
            job_result.job_errors[0]
            == "No records found for Contact in the target org."
        )
        assert job_result.records_processed == 0
        assert job_result.total_row_errors == 0

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_user_selection_filter_success(self, download_mock):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
            selection_filter='WHERE LastName in ("Sample Name")',
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content with a single record
        download_mock.return_value = io.StringIO('[{"Id":"003000000000001"}]')

        # Mock the _wait_for_job method to simulate a successful job
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        # Prepare input records
        records = iter([["Test1"], ["Test2"], ["Test3"]])

        # Execute the select_records operation
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 3
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_user_selection_filter_order_success(self, download_mock):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
            selection_filter="ORDER BY CreatedDate",
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content with a single record
        download_mock.return_value = io.StringIO(
            '[{"Id":"003000000000003"}, {"Id":"003000000000001"}, {"Id":"003000000000002"}]'
        )
        # Mock the _wait_for_job method to simulate a successful job
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        # Prepare input records
        records = iter([["Test1"], ["Test2"], ["Test3"]])

        # Execute the select_records operation
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results are in the order given by user query
        assert results[0].id == "003000000000003"
        assert results[1].id == "003000000000001"
        assert results[2].id == "003000000000002"

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_user_selection_filter_failure(self, download_mock):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
            selection_filter='WHERE LastName in ("Sample Name")',
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content with a single record
        download_mock.side_effect = BulkDataException("MALFORMED QUERY")
        # Prepare input records
        records = iter([["Test1"], ["Test2"], ["Test3"]])

        # Execute the select_records operation
        step.start()
        with pytest.raises(BulkDataException):
            step.select_records(records)

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_similarity_strategy_success(self, download_mock):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["Name", "Email"],
            selection_strategy=SelectStrategy.SIMILARITY,
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content with a single record
        download_mock.return_value = io.StringIO(
            """[{"Id":"003000000000001", "Name":"Jawad", "Email":"mjawadtp@example.com"}, {"Id":"003000000000002", "Name":"Aditya", "Email":"aditya@example.com"}, {"Id":"003000000000003", "Name":"Tom", "Email":"tom@example.com"}]"""
        )

        # Mock the _wait_for_job method to simulate a successful job
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        # Prepare input records
        records = iter(
            [
                ["Jawad", "mjawadtp@example.com"],
                ["Aditya", "aditya@example.com"],
                ["Tom", "cruise@example.com"],
            ]
        )

        # Execute the select_records operation
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())

        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000002", success=True, error="", created=False
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000003", success=True, error="", created=False
                )
            )
            == 1
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_similarity_strategy_failure__no_records(
        self, download_mock
    ):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["Id", "Name", "Email"],
            selection_strategy=SelectStrategy.SIMILARITY,
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content indicating no records found
        download_mock.return_value = io.StringIO("[]")

        # Mock the _wait_for_job method to simulate a successful job
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        # Prepare input records
        records = iter(
            [
                ["Jawad", "mjawadtp@example.com"],
                ["Aditya", "aditya@example.com"],
                ["Tom", "cruise@example.com"],
            ]
        )

        # Execute the select_records operation
        step.start()
        step.select_records(records)
        step.end()

        # Get the job result and assert its properties for failure scenario
        job_result = step.job_result
        assert job_result.status == DataOperationStatus.JOB_FAILURE
        assert (
            job_result.job_errors[0]
            == "No records found for Contact in the target org."
        )
        assert job_result.records_processed == 0
        assert job_result.total_row_errors == 0

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_similarity_strategy_parent_level_records__polymorphic(
        self, download_mock
    ):
        mock_describe_calls()
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Event",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10},
            context=context,
            fields=[
                "Subject",
                "Who.Contact.Name",
                "Who.Contact.Email",
                "Who.Lead.Name",
                "Who.Lead.Company",
                "WhoId",
            ],
            selection_strategy=SelectStrategy.SIMILARITY,
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        download_mock.return_value = io.StringIO(
            """[
                {"Id": "003000000000001", "Subject": "Sample Event 1", "Who":{ "attributes": {"type": "Contact"}, "Id": "abcd1234", "Name": "Sample Contact", "Email": "contact@example.com"}},
                { "Id": "003000000000002", "Subject": "Sample Event 2", "Who":{ "attributes": {"type": "Lead"}, "Id": "qwer1234", "Name": "Sample Lead", "Company": "Salesforce"}}
            ]"""
        )

        records = iter(
            [
                [
                    "Sample Event 1",
                    "Sample Contact",
                    "contact@example.com",
                    "",
                    "",
                    "lkjh1234",
                ],
                ["Sample Event 2", "", "", "Sample Lead", "Salesforce", "poiu1234"],
            ]
        )
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 2  # Expect 2 results (matching the input records count)

        # Assert that all results have the expected ID, success, and created values
        assert results[0] == DataOperationResult(
            id="003000000000001", success=True, error="", created=False
        )
        assert results[1] == DataOperationResult(
            id="003000000000002", success=True, error="", created=False
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_similarity_strategy_parent_level_records__non_polymorphic(
        self, download_mock
    ):
        mock_describe_calls()
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10},
            context=context,
            fields=["Name", "Account.Name", "Account.AccountNumber", "AccountId"],
            selection_strategy=SelectStrategy.SIMILARITY,
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        download_mock.return_value = io.StringIO(
            """[
                {"Id": "003000000000001", "Name": "Sample Contact 1", "Account":{ "attributes": {"type": "Account"}, "Id": "abcd1234", "Name": "Sample Account", "AccountNumber": 123456}},
                { "Id": "003000000000002", "Subject": "Sample Contact 2", "Account": null}
            ]"""
        )

        records = iter(
            [
                ["Sample Contact 3", "Sample Account", "123456", "poiu1234"],
                ["Sample Contact 4", "", "", ""],
            ]
        )
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 2  # Expect 2 results (matching the input records count)

        # Assert that all results have the expected ID, success, and created values
        assert results[0] == DataOperationResult(
            id="003000000000001", success=True, error="", created=False
        )
        assert results[1] == DataOperationResult(
            id="003000000000002", success=True, error="", created=False
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_similarity_strategy_priority_fields(self, download_mock):
        mock_describe_calls()
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        step_1 = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10},
            context=context,
            fields=[
                "Name",
                "Email",
                "Account.Name",
                "Account.AccountNumber",
                "AccountId",
            ],
            selection_strategy=SelectStrategy.SIMILARITY,
            selection_priority_fields={"Name": "Name", "Email": "Email"},
        )

        step_2 = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10},
            context=context,
            fields=[
                "Name",
                "Email",
                "Account.Name",
                "Account.AccountNumber",
                "AccountId",
            ],
            selection_strategy=SelectStrategy.SIMILARITY,
            selection_priority_fields={
                "Account.Name": "Account.Name",
                "Account.AccountNumber": "Account.AccountNumber",
            },
        )

        # Mock Bulk API responses
        step_1.bulk.endpoint = "https://test"
        step_1.bulk.create_query_job.return_value = "JOB"
        step_1.bulk.query.return_value = "BATCH"
        step_1.bulk.get_query_batch_result_ids.return_value = ["RESULT"]
        step_2.bulk.endpoint = "https://test"
        step_2.bulk.create_query_job.return_value = "JOB"
        step_2.bulk.query.return_value = "BATCH"
        step_2.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        sample_response = [
            {
                "Id": "003000000000001",
                "Name": "Bob The Builder",
                "Email": "bob@yahoo.org",
                "Account": {
                    "attributes": {"type": "Account"},
                    "Id": "abcd1234",
                    "Name": "Jawad TP",
                    "AccountNumber": 567890,
                },
            },
            {
                "Id": "003000000000002",
                "Name": "Tom Cruise",
                "Email": "tom@exmaple.com",
                "Account": {
                    "attributes": {"type": "Account"},
                    "Id": "qwer1234",
                    "Name": "Aditya B",
                    "AccountNumber": 123456,
                },
            },
        ]

        download_mock.side_effect = [
            io.StringIO(f"""{json.dumps(sample_response)}"""),
            io.StringIO(f"""{json.dumps(sample_response)}"""),
        ]

        records = iter(
            [
                ["Bob The Builder", "bob@yahoo.org", "Aditya B", "123456", "poiu1234"],
            ]
        )
        records_1, records_2 = tee(records)
        step_1.start()
        step_1.select_records(records_1)
        step_1.end()

        step_2.start()
        step_2.select_records(records_2)
        step_2.end()

        # Get the results and assert their properties
        results_1 = list(step_1.get_results())
        results_2 = list(step_2.get_results())
        assert (
            len(results_1) == 1
        )  # Expect 1 results (matching the input records count)
        assert (
            len(results_2) == 1
        )  # Expect 1 results (matching the input records count)

        # Assert that all results have the expected ID, success, and created values
        # Prioritizes Name and Email
        assert results_1[0] == DataOperationResult(
            id="003000000000001", success=True, error="", created=False
        )
        # Prioritizes Account.Name and Account.AccountNumber
        assert results_2[0] == DataOperationResult(
            id="003000000000002", success=True, error="", created=False
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_process_insert_records_success(self, download_mock):
        # Mock context and insert records
        context = mock.Mock()
        insert_records = iter([["John", "Doe"], ["Jane", "Smith"]])
        selected_records = [None, None]

        # Mock insert fields splitting
        insert_fields = ["FirstName", "LastName"]
        with mock.patch(
            "cumulusci.tasks.bulkdata.step.split_and_filter_fields",
            return_value=(insert_fields, None),
        ) as split_mock:
            step = BulkApiDmlOperation(
                sobject="Contact",
                operation=DataOperationType.QUERY,
                api_options={"batch_size": 10},
                context=context,
                fields=["FirstName", "LastName"],
            )

            # Mock Bulk API
            step.bulk.endpoint = "https://test"
            step.bulk.create_insert_job.return_value = "JOB"
            step.bulk.get_insert_batch_result_ids.return_value = ["RESULT"]

            # Mock the downloaded CSV content with successful results
            download_mock.return_value = io.StringIO(
                "Id,Success,Created\n0011k00003E8xAaAAI,true,true\n0011k00003E8xAbAAJ,true,true\n"
            )

            # Mock sub-operation for BulkApiDmlOperation
            insert_step = mock.Mock(spec=BulkApiDmlOperation)
            insert_step.start = mock.Mock()
            insert_step.load_records = mock.Mock()
            insert_step.end = mock.Mock()
            insert_step.batch_ids = ["BATCH1"]
            insert_step.bulk = mock.Mock()
            insert_step.bulk.endpoint = "https://test"
            insert_step.job_id = "JOB"

            with mock.patch(
                "cumulusci.tasks.bulkdata.step.BulkApiDmlOperation",
                return_value=insert_step,
            ):
                step._process_insert_records(insert_records, selected_records)

                # Assertions for split fields and sub-operation
                split_mock.assert_called_once_with(fields=["FirstName", "LastName"])
                insert_step.start.assert_called_once()
                insert_step.load_records.assert_called_once_with(insert_records)
                insert_step.end.assert_called_once()

                # Validate the download file interactions
                download_mock.assert_called_once_with(
                    "https://test/job/JOB/batch/BATCH1/result", insert_step.bulk
                )

                # Validate that selected_records is updated with insert results
                assert selected_records == [
                    {"id": "0011k00003E8xAaAAI", "success": True, "created": True},
                    {"id": "0011k00003E8xAbAAJ", "success": True, "created": True},
                ]

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_process_insert_records_failure(self, download_mock):
        # Mock context and insert records
        context = mock.Mock()
        insert_records = iter([["John", "Doe"], ["Jane", "Smith"]])
        selected_records = [None, None]

        # Mock insert fields splitting
        insert_fields = ["FirstName", "LastName"]
        with mock.patch(
            "cumulusci.tasks.bulkdata.step.split_and_filter_fields",
            return_value=(insert_fields, None),
        ):
            step = BulkApiDmlOperation(
                sobject="Contact",
                operation=DataOperationType.QUERY,
                api_options={"batch_size": 10},
                context=context,
                fields=["FirstName", "LastName"],
            )

            # Mock failure during results download
            download_mock.side_effect = Exception("Download failed")

            # Mock sub-operation for BulkApiDmlOperation
            insert_step = mock.Mock(spec=BulkApiDmlOperation)
            insert_step.start = mock.Mock()
            insert_step.load_records = mock.Mock()
            insert_step.end = mock.Mock()
            insert_step.batch_ids = ["BATCH1"]
            insert_step.bulk = mock.Mock()
            insert_step.bulk.endpoint = "https://test"
            insert_step.job_id = "JOB"

            with mock.patch(
                "cumulusci.tasks.bulkdata.step.BulkApiDmlOperation",
                return_value=insert_step,
            ):
                with pytest.raises(BulkDataException) as excinfo:
                    step._process_insert_records(insert_records, selected_records)

                # Validate that the exception is raised with the correct message
                assert "Failed to download results for batch BATCH1" in str(
                    excinfo.value
                )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_similarity_strategy__insert_records__non_zero_threshold(
        self, download_mock
    ):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        # Add step with threshold
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["Name", "Email"],
            selection_strategy=SelectStrategy.SIMILARITY,
            threshold=0.3,
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content with a single record
        select_results = io.StringIO(
            """[{"Id":"003000000000001", "Name":"Jawad", "Email":"mjawadtp@example.com"}]"""
        )
        insert_results = io.StringIO(
            "Id,Success,Created\n003000000000002,true,true\n003000000000003,true,true\n"
        )
        download_mock.side_effect = [select_results, insert_results]

        # Mock the _wait_for_job method to simulate a successful job
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        # Prepare input records
        records = iter(
            [
                ["Jawad", "mjawadtp@example.com"],
                ["Aditya", "aditya@example.com"],
                ["Tom", "cruise@example.com"],
            ]
        )

        # Mock sub-operation for BulkApiDmlOperation
        insert_step = mock.Mock(spec=BulkApiDmlOperation)
        insert_step.start = mock.Mock()
        insert_step.load_records = mock.Mock()
        insert_step.end = mock.Mock()
        insert_step.batch_ids = ["BATCH1"]
        insert_step.bulk = mock.Mock()
        insert_step.bulk.endpoint = "https://test"
        insert_step.job_id = "JOB"

        with mock.patch(
            "cumulusci.tasks.bulkdata.step.BulkApiDmlOperation",
            return_value=insert_step,
        ):
            # Execute the select_records operation
            step.start()
            step.select_records(records)
            step.end()

        # Get the results and assert their properties
        results = list(step.get_results())

        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000002", success=True, error="", created=True
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000003", success=True, error="", created=True
                )
            )
            == 1
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_similarity_strategy__insert_records__zero_threshold(
        self, download_mock
    ):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        # Add step with threshold
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["Name", "Email"],
            selection_strategy=SelectStrategy.SIMILARITY,
            threshold=0,
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content with a single record
        select_results = io.StringIO(
            """[{"Id":"003000000000001", "Name":"Jawad", "Email":"mjawadtp@example.com"}]"""
        )
        insert_results = io.StringIO(
            "Id,Success,Created\n003000000000002,true,true\n003000000000003,true,true\n"
        )
        download_mock.side_effect = [select_results, insert_results]

        # Mock the _wait_for_job method to simulate a successful job
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        # Prepare input records
        records = iter(
            [
                ["Jawad", "mjawadtp@example.com"],
                ["Aditya", "aditya@example.com"],
                ["Tom", "cruise@example.com"],
            ]
        )

        # Mock sub-operation for BulkApiDmlOperation
        insert_step = mock.Mock(spec=BulkApiDmlOperation)
        insert_step.start = mock.Mock()
        insert_step.load_records = mock.Mock()
        insert_step.end = mock.Mock()
        insert_step.batch_ids = ["BATCH1"]
        insert_step.bulk = mock.Mock()
        insert_step.bulk.endpoint = "https://test"
        insert_step.job_id = "JOB"

        with mock.patch(
            "cumulusci.tasks.bulkdata.step.BulkApiDmlOperation",
            return_value=insert_step,
        ):
            # Execute the select_records operation
            step.start()
            step.select_records(records)
            step.end()

        # Get the results and assert their properties
        results = list(step.get_results())

        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000002", success=True, error="", created=True
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000003", success=True, error="", created=True
                )
            )
            == 1
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.download_file")
    def test_select_records_similarity_strategy__insert_records__no_select_records(
        self, download_mock
    ):
        # Set up mock context and BulkApiDmlOperation
        context = mock.Mock()
        # Add step with threshold
        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=context,
            fields=["Name", "Email"],
            selection_strategy=SelectStrategy.SIMILARITY,
            threshold=0.3,
        )

        # Mock Bulk API responses
        step.bulk.endpoint = "https://test"
        step.bulk.create_query_job.return_value = "JOB"
        step.bulk.query.return_value = "BATCH"
        step.bulk.get_query_batch_result_ids.return_value = ["RESULT"]

        # Mock the downloaded CSV content with a single record
        select_results = io.StringIO("""[]""")
        insert_results = io.StringIO(
            "Id,Success,Created\n003000000000001,true,true\n003000000000002,true,true\n003000000000003,true,true\n"
        )
        download_mock.side_effect = [select_results, insert_results]

        # Mock the _wait_for_job method to simulate a successful job
        step._wait_for_job = mock.Mock()
        step._wait_for_job.return_value = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        # Prepare input records
        records = iter(
            [
                ["Jawad", "mjawadtp@example.com"],
                ["Aditya", "aditya@example.com"],
                ["Tom", "cruise@example.com"],
            ]
        )

        # Mock sub-operation for BulkApiDmlOperation
        insert_step = mock.Mock(spec=BulkApiDmlOperation)
        insert_step.start = mock.Mock()
        insert_step.load_records = mock.Mock()
        insert_step.end = mock.Mock()
        insert_step.batch_ids = ["BATCH1"]
        insert_step.bulk = mock.Mock()
        insert_step.bulk.endpoint = "https://test"
        insert_step.job_id = "JOB"

        with mock.patch(
            "cumulusci.tasks.bulkdata.step.BulkApiDmlOperation",
            return_value=insert_step,
        ):
            # Execute the select_records operation
            step.start()
            step.select_records(records)
            step.end()

        # Get the results and assert their properties
        results = list(step.get_results())

        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=True
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000002", success=True, error="", created=True
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000003", success=True, error="", created=True
                )
            )
            == 1
        )

    def test_batch(self):
        context = mock.Mock()

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={"batch_size": 2},
            context=context,
            fields=["LastName"],
        )

        records = iter([["Test"], ["Test2"], ["Test3"]])
        results = list(step._batch(records, n=2))

        assert len(results) == 2
        assert list(results[0]) == [
            '"LastName"\r\n'.encode("utf-8"),
            '"Test"\r\n'.encode("utf-8"),
            '"Test2"\r\n'.encode("utf-8"),
        ]
        assert list(results[1]) == [
            '"LastName"\r\n'.encode("utf-8"),
            '"Test3"\r\n'.encode("utf-8"),
        ]

    def test_batch__character_limit(self):
        context = mock.Mock()

        step = BulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={"batch_size": 2},
            context=context,
            fields=["LastName"],
        )

        records = [["Test"], ["Test2"], ["Test3"]]

        csv_rows = [step._serialize_csv_record(step.fields)]
        for r in records:
            csv_rows.append(step._serialize_csv_record(r))

        char_limit = sum([len(r) for r in csv_rows]) - 1

        # Ask for batches of three, but we
        # should get batches of 2 back
        results = list(step._batch(iter(records), n=3, char_limit=char_limit))

        assert len(results) == 2
        assert list(results[0]) == [
            '"LastName"\r\n'.encode("utf-8"),
            '"Test"\r\n'.encode("utf-8"),
            '"Test2"\r\n'.encode("utf-8"),
        ]
        assert list(results[1]) == [
            '"LastName"\r\n'.encode("utf-8"),
            '"Test3"\r\n'.encode("utf-8"),
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
            DataOperationResult("003000000000001", True, None, True),
            DataOperationResult("003000000000002", True, None, True),
            DataOperationResult(None, False, "error", False),
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

        with pytest.raises(BulkDataException):
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
            DataOperationResult("003000000000001", True, None, True),
            DataOperationResult("003000000000002", True, None, True),
            DataOperationResult(None, False, "error", False),
        ]


class TestRestApiQueryOperation:
    def test_query(self):
        context = mock.Mock()
        context.sf.query.return_value = {
            "totalSize": 2,
            "done": True,
            "records": [
                {
                    "Id": "003000000000001",
                    "LastName": "Narvaez",
                    "Email": "wayne@example.com",
                },
                {"Id": "003000000000002", "LastName": "De Vries", "Email": None},
            ],
        }

        query_op = RestApiQueryOperation(
            sobject="Contact",
            fields=["Id", "LastName", "Email"],
            api_options={},
            context=context,
            query="SELECT Id, LastName,  Email FROM Contact",
        )

        query_op.query()

        assert query_op.job_result == DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        assert list(query_op.get_results()) == [
            ["003000000000001", "Narvaez", "wayne@example.com"],
            ["003000000000002", "De Vries", ""],
        ]

    def test_query_batches(self):
        context = mock.Mock()
        context.sf.query.return_value = {
            "totalSize": 2,
            "done": False,
            "records": [
                {
                    "Id": "003000000000001",
                    "LastName": "Narvaez",
                    "Email": "wayne@example.com",
                }
            ],
            "nextRecordsUrl": "test",
        }

        context.sf.query_more.return_value = {
            "totalSize": 2,
            "done": True,
            "records": [
                {"Id": "003000000000002", "LastName": "De Vries", "Email": None}
            ],
        }

        query_op = RestApiQueryOperation(
            sobject="Contact",
            fields=["Id", "LastName", "Email"],
            api_options={},
            context=context,
            query="SELECT Id, LastName,  Email FROM Contact",
        )

        query_op.query()

        assert query_op.job_result == DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        assert list(query_op.get_results()) == [
            ["003000000000001", "Narvaez", "wayne@example.com"],
            ["003000000000002", "De Vries", ""],
        ]


class TestRestApiDmlOperation:
    @responses.activate
    def test_insert_dml_operation(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )

        recs = [["Fred", "Narvaez"], [None, "De Vries"], ["Hiroko", "Aito"]]

        dml_op = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={"batch_size": 2},
            context=task,
            fields=["FirstName", "LastName"],
        )

        dml_op.start()
        dml_op.load_records(iter(recs))
        dml_op.end()

        assert dml_op.job_result == DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 3, 0
        )
        assert list(dml_op.get_results()) == [
            DataOperationResult("003000000000001", True, "", True),
            DataOperationResult("003000000000002", True, "", True),
            DataOperationResult("003000000000003", True, "", True),
        ]

    @responses.activate
    def test_get_prev_record_values(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )

        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=task,
            fields=["LastName"],
        )

        results = {
            "records": [
                {"LastName": "Test1", "Id": "Id1"},
                {"LastName": "Test2", "Id": "Id2"},
            ]
        }
        expected_record_values = [["Test1", "Id1"], ["Test2", "Id2"]]
        expected_relevant_fields = ("Id", "LastName")
        step.sf.query = mock.Mock()
        step.sf.query.return_value = results
        records = iter([["Test1"], ["Test2"], ["Test3"]])
        prev_record_values, relevant_fields = step.get_prev_record_values(records)

        assert sorted(map(sorted, prev_record_values)) == sorted(
            map(sorted, expected_record_values)
        )
        assert set(relevant_fields) == set(expected_relevant_fields)

    @responses.activate
    def test_select_records_standard_strategy_success(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=task,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
        )

        results = {
            "records": [
                {"Id": "003000000000001"},
            ],
            "done": True,
        }
        step.sf.restful = mock.Mock()
        step.sf.restful.return_value = results
        records = iter([["Test1"], ["Test2"], ["Test3"]])
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 3
        )

    @responses.activate
    def test_select_records_zero_load_records(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=task,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
        )

        results = {
            "records": [],
            "done": True,
        }
        step.sf.restful = mock.Mock()
        step.sf.restful.return_value = results
        records = iter([])
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 0  # Expect 0 results (matching the input records count)

    @responses.activate
    def test_select_records_standard_strategy_success_pagination(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=task,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
        )

        # Set up pagination: First call returns done=False, second call returns done=True
        step.sf.restful = mock.Mock(
            side_effect=[
                {
                    "records": [{"Id": "003000000000001"}, {"Id": "003000000000002"}],
                    "done": False,  # Pagination in progress
                    "nextRecordsUrl": "/services/data/vXX.X/query/next-records",
                },
            ]
        )

        step.sf.query_more = mock.Mock(
            side_effect=[
                {"records": [{"Id": "003000000000003"}], "done": True}  # Final page
            ]
        )

        records = iter([["Test1"], ["Test2"], ["Test3"]])
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 3  # Expect 3 results (matching the input records count)

        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000002", success=True, error="", created=False
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000003", success=True, error="", created=False
                )
            )
            == 1
        )

    @responses.activate
    def test_select_records_standard_strategy_failure__no_records(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=task,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
        )

        results = {"records": [], "done": True}
        step.sf.restful = mock.Mock()
        step.sf.restful.return_value = results
        records = iter([["Test1"], ["Test2"], ["Test3"]])
        step.start()
        step.select_records(records)
        step.end()

        # Get the job result and assert its properties for failure scenario
        job_result = step.job_result
        assert job_result.status == DataOperationStatus.JOB_FAILURE
        assert (
            job_result.job_errors[0]
            == "No records found for Contact in the target org."
        )
        assert job_result.records_processed == 0
        assert job_result.total_row_errors == 0

    @responses.activate
    def test_select_records_user_selection_filter_success(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=task,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
            selection_filter='WHERE LastName IN ("Sample Name")',
        )

        results = {
            "records": [
                {"Id": "003000000000001"},
            ],
            "done": True,
        }
        step.sf.restful = mock.Mock()
        step.sf.restful.return_value = results
        records = iter([["Test1"], ["Test2"], ["Test3"]])
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 3
        )

    @responses.activate
    def test_select_records_user_selection_filter_order_success(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=task,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
            selection_filter="ORDER BY CreatedDate",
        )

        results = {
            "records": [
                {"Id": "003000000000003"},
                {"Id": "003000000000001"},
                {"Id": "003000000000002"},
            ],
            "done": True,
        }
        step.sf.restful = mock.Mock()
        step.sf.restful.return_value = results
        records = iter([["Test1"], ["Test2"], ["Test3"]])
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results are in the order of user_query
        assert results[0].id == "003000000000003"
        assert results[1].id == "003000000000001"
        assert results[2].id == "003000000000002"

    @responses.activate
    def test_select_records_user_selection_filter_failure(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=task,
            fields=["LastName"],
            selection_strategy=SelectStrategy.STANDARD,
            selection_filter="MALFORMED FILTER",  # Applying malformed filter
        )

        step.sf.restful = mock.Mock()
        step.sf.restful.side_effect = Exception("MALFORMED QUERY")
        records = iter([["Test1"], ["Test2"], ["Test3"]])
        step.start()
        with pytest.raises(Exception):
            step.select_records(records)

    @responses.activate
    def test_select_records_similarity_strategy_success(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=task,
            fields=["Name", "Email"],
            selection_strategy=SelectStrategy.SIMILARITY,
        )

        results_first_call = {
            "records": [
                {
                    "Id": "003000000000001",
                    "Name": "Jawad",
                    "Email": "mjawadtp@example.com",
                },
                {
                    "Id": "003000000000002",
                    "Name": "Aditya",
                    "Email": "aditya@example.com",
                },
                {
                    "Id": "003000000000003",
                    "Name": "Tom Cruise",
                    "Email": "tomcruise@example.com",
                },
            ],
            "done": True,
        }

        # First call returns `results_first_call`, second call returns an empty list
        step.sf.restful = mock.Mock(
            side_effect=[results_first_call, {"records": [], "done": True}]
        )
        records = iter(
            [
                ["Jawad", "mjawadtp@example.com"],
                ["Aditya", "aditya@example.com"],
                ["Tom Cruise", "tom@example.com"],
            ]
        )
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000002", success=True, error="", created=False
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000003", success=True, error="", created=False
                )
            )
            == 1
        )

    @responses.activate
    def test_select_records_similarity_strategy_failure__no_records(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10, "update_key": "LastName"},
            context=task,
            fields=["Name", "Email"],
            selection_strategy=SelectStrategy.SIMILARITY,
        )

        results = {"records": [], "done": True}
        step.sf.restful = mock.Mock()
        step.sf.restful.return_value = results
        records = iter(
            [
                ["Id: 1", "Jawad", "mjawadtp@example.com"],
                ["Id: 2", "Aditya", "aditya@example.com"],
                ["Id: 2", "Tom", "tom@example.com"],
            ]
        )
        step.start()
        step.select_records(records)
        step.end()

        # Get the job result and assert its properties for failure scenario
        job_result = step.job_result
        assert job_result.status == DataOperationStatus.JOB_FAILURE
        assert (
            job_result.job_errors[0]
            == "No records found for Contact in the target org."
        )
        assert job_result.records_processed == 0
        assert job_result.total_row_errors == 0

    @responses.activate
    def test_select_records_similarity_strategy_parent_level_records__polymorphic(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step = RestApiDmlOperation(
            sobject="Event",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10},
            context=task,
            fields=[
                "Subject",
                "Who.Contact.Name",
                "Who.Contact.Email",
                "Who.Lead.Name",
                "Who.Lead.Company",
                "WhoId",
            ],
            selection_strategy=SelectStrategy.SIMILARITY,
        )

        step.sf.restful = mock.Mock(
            side_effect=[
                {
                    "records": [
                        {
                            "Id": "003000000000001",
                            "Subject": "Sample Event 1",
                            "Who": {
                                "attributes": {"type": "Contact"},
                                "Id": "abcd1234",
                                "Name": "Sample Contact",
                                "Email": "contact@example.com",
                            },
                        },
                        {
                            "Id": "003000000000002",
                            "Subject": "Sample Event 2",
                            "Who": {
                                "attributes": {"type": "Lead"},
                                "Id": "qwer1234",
                                "Name": "Sample Lead",
                                "Company": "Salesforce",
                            },
                        },
                    ],
                    "done": True,
                },
            ]
        )

        records = iter(
            [
                [
                    "Sample Event 1",
                    "Sample Contact",
                    "contact@example.com",
                    "",
                    "",
                    "poiu1234",
                ],
                ["Sample Event 2", "", "", "Sample Lead", "Salesforce", "lkjh1234"],
            ]
        )
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 2  # Expect 2 results (matching the input records count)

        # Assert that all results have the expected ID, success, and created values
        assert results[0] == DataOperationResult(
            id="003000000000001", success=True, error="", created=False
        )
        assert results[1] == DataOperationResult(
            id="003000000000002", success=True, error="", created=False
        )

    @responses.activate
    def test_select_records_similarity_strategy_parent_level_records__non_polymorphic(
        self,
    ):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10},
            context=task,
            fields=["Name", "Account.Name", "Account.AccountNumber", "AccountId"],
            selection_strategy=SelectStrategy.SIMILARITY,
        )

        step.sf.restful = mock.Mock(
            side_effect=[
                {
                    "records": [
                        {
                            "Id": "003000000000001",
                            "Name": "Sample Contact 1",
                            "Account": {
                                "attributes": {"type": "Account"},
                                "Id": "abcd1234",
                                "Name": "Sample Account",
                                "AccountNumber": 123456,
                            },
                        },
                        {
                            "Id": "003000000000002",
                            "Name": "Sample Contact 2",
                            "Account": None,
                        },
                    ],
                    "done": True,
                },
            ]
        )

        records = iter(
            [
                ["Sample Contact 3", "Sample Account", "123456", "poiu1234"],
                ["Sample Contact 4", "", "", ""],
            ]
        )
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 2  # Expect 2 results (matching the input records count)

        # Assert that all results have the expected ID, success, and created values
        assert results[0] == DataOperationResult(
            id="003000000000001", success=True, error="", created=False
        )
        assert results[1] == DataOperationResult(
            id="003000000000002", success=True, error="", created=False
        )

    @responses.activate
    def test_select_records_similarity_strategy_priority_fields(self):
        mock_describe_calls()
        task_1 = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task_1.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task_1._init_task()

        task_2 = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task_2.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task_2._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )
        step_1 = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10},
            context=task_1,
            fields=[
                "Name",
                "Email",
                "Account.Name",
                "Account.AccountNumber",
                "AccountId",
            ],
            selection_strategy=SelectStrategy.SIMILARITY,
            selection_priority_fields={"Name": "Name", "Email": "Email"},
        )

        step_2 = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.QUERY,
            api_options={"batch_size": 10},
            context=task_2,
            fields=[
                "Name",
                "Email",
                "Account.Name",
                "Account.AccountNumber",
                "AccountId",
            ],
            selection_strategy=SelectStrategy.SIMILARITY,
            selection_priority_fields={
                "Account.Name": "Account.Name",
                "Account.AccountNumber": "Account.AccountNumber",
            },
        )

        sample_response = [
            {
                "records": [
                    {
                        "Id": "003000000000001",
                        "Name": "Bob The Builder",
                        "Email": "bob@yahoo.org",
                        "Account": {
                            "attributes": {"type": "Account"},
                            "Id": "abcd1234",
                            "Name": "Jawad TP",
                            "AccountNumber": 567890,
                        },
                    },
                    {
                        "Id": "003000000000002",
                        "Name": "Tom Cruise",
                        "Email": "tom@exmaple.com",
                        "Account": {
                            "attributes": {"type": "Account"},
                            "Id": "qwer1234",
                            "Name": "Aditya B",
                            "AccountNumber": 123456,
                        },
                    },
                ],
                "done": True,
            },
        ]

        step_1.sf.restful = mock.Mock(side_effect=sample_response)
        step_2.sf.restful = mock.Mock(side_effect=sample_response)

        records = iter(
            [
                ["Bob The Builder", "bob@yahoo.org", "Aditya B", "123456", "poiu1234"],
            ]
        )
        records_1, records_2 = tee(records)
        step_1.start()
        step_1.select_records(records_1)
        step_1.end()

        step_2.start()
        step_2.select_records(records_2)
        step_2.end()

        # Get the results and assert their properties
        results_1 = list(step_1.get_results())
        results_2 = list(step_2.get_results())
        assert (
            len(results_1) == 1
        )  # Expect 1 results (matching the input records count)
        assert (
            len(results_2) == 1
        )  # Expect 1 results (matching the input records count)

        # Assert that all results have the expected ID, success, and created values
        # Prioritizes Name and Email
        assert results_1[0] == DataOperationResult(
            id="003000000000001", success=True, error="", created=False
        )
        # Prioritizes Account.Name and Account.AccountNumber
        assert results_2[0] == DataOperationResult(
            id="003000000000002", success=True, error="", created=False
        )

    @responses.activate
    def test_process_insert_records_success(self):
        # Mock describe calls
        mock_describe_calls()

        # Create a task and mock project config
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        # Prepare inputs
        insert_records = iter(
            [
                ["Jawad", "mjawadtp@example.com"],
                ["Aditya", "aditya@example.com"],
                ["Tom Cruise", "tomcruise@example.com"],
            ]
        )
        selected_records = [None, None, None]

        # Mock fields splitting
        insert_fields = ["Name", "Email"]
        with mock.patch(
            "cumulusci.tasks.bulkdata.step.split_and_filter_fields",
            return_value=(insert_fields, None),
        ) as split_mock:
            # Mock the instance of RestApiDmlOperation
            mock_rest_api_dml_operation = mock.create_autospec(
                RestApiDmlOperation, instance=True
            )
            mock_rest_api_dml_operation.results = [
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
                {"id": "003000000000003", "success": True},
            ]

            with mock.patch(
                "cumulusci.tasks.bulkdata.step.RestApiDmlOperation",
                return_value=mock_rest_api_dml_operation,
            ):
                # Call the function
                step = RestApiDmlOperation(
                    sobject="Contact",
                    operation=DataOperationType.INSERT,
                    api_options={"batch_size": 10},
                    context=task,
                    fields=["Name", "Email"],
                )
                step._process_insert_records(insert_records, selected_records)

                # Assert the mocked splitting is called
                split_mock.assert_called_once_with(fields=["Name", "Email"])

                # Validate that `selected_records` is updated correctly
                assert selected_records == [
                    {"id": "003000000000001", "success": True},
                    {"id": "003000000000002", "success": True},
                    {"id": "003000000000003", "success": True},
                ]

                # Validate the operation sequence
                mock_rest_api_dml_operation.start.assert_called_once()
                mock_rest_api_dml_operation.load_records.assert_called_once_with(
                    insert_records
                )
                mock_rest_api_dml_operation.end.assert_called_once()

    @responses.activate
    def test_process_insert_records_failure(self):
        # Mock describe calls
        mock_describe_calls()

        # Create a task and mock project config
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        # Prepare inputs
        insert_records = iter(
            [
                ["Jawad", "mjawadtp@example.com"],
                ["Aditya", "aditya@example.com"],
            ]
        )
        selected_records = [None, None]

        # Mock fields splitting
        insert_fields = ["Name", "Email"]
        with mock.patch(
            "cumulusci.tasks.bulkdata.step.split_and_filter_fields",
            return_value=(insert_fields, None),
        ) as split_mock:
            # Mock the instance of RestApiDmlOperation
            mock_rest_api_dml_operation = mock.create_autospec(
                RestApiDmlOperation, instance=True
            )
            mock_rest_api_dml_operation.results = (
                None  # Simulate no results due to an exception
            )

            # Simulate an exception during processing results
            mock_rest_api_dml_operation.load_records.side_effect = BulkDataException(
                "Simulated failure"
            )

            with mock.patch(
                "cumulusci.tasks.bulkdata.step.RestApiDmlOperation",
                return_value=mock_rest_api_dml_operation,
            ):
                # Call the function and verify that it raises the expected exception
                step = RestApiDmlOperation(
                    sobject="Contact",
                    operation=DataOperationType.INSERT,
                    api_options={"batch_size": 10},
                    context=task,
                    fields=["Name", "Email"],
                )
                with pytest.raises(BulkDataException):
                    step._process_insert_records(insert_records, selected_records)

                # Assert the mocked splitting is called
                split_mock.assert_called_once_with(fields=["Name", "Email"])

                # Validate that `selected_records` remains unchanged
                assert selected_records == [None, None]

                # Validate the operation sequence
                mock_rest_api_dml_operation.start.assert_called_once()
                mock_rest_api_dml_operation.load_records.assert_called_once_with(
                    insert_records
                )
                mock_rest_api_dml_operation.end.assert_not_called()

    @responses.activate
    def test_select_records_similarity_strategy__insert_records__non_zero_threshold(
        self,
    ):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        # Create step with threshold
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10},
            context=task,
            fields=["Name", "Email"],
            selection_strategy=SelectStrategy.SIMILARITY,
            threshold=0.3,
        )

        results_select_call = {
            "records": [
                {
                    "Id": "003000000000001",
                    "Name": "Jawad",
                    "Email": "mjawadtp@example.com",
                },
            ],
            "done": True,
        }

        results_insert_call = [
            {"id": "003000000000002", "success": True, "created": True},
            {"id": "003000000000003", "success": True, "created": True},
        ]

        step.sf.restful = mock.Mock(
            side_effect=[results_select_call, results_insert_call]
        )
        records = iter(
            [
                ["Jawad", "mjawadtp@example.com"],
                ["Aditya", "aditya@example.com"],
                ["Tom Cruise", "tom@example.com"],
            ]
        )
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000002", success=True, error="", created=True
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000003", success=True, error="", created=True
                )
            )
            == 1
        )

    @responses.activate
    def test_select_records_similarity_strategy__insert_records__zero_threshold(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        # Create step with threshold
        step = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPSERT,
            api_options={"batch_size": 10},
            context=task,
            fields=["Name", "Email"],
            selection_strategy=SelectStrategy.SIMILARITY,
            threshold=0,
        )

        results_select_call = {
            "records": [
                {
                    "Id": "003000000000001",
                    "Name": "Jawad",
                    "Email": "mjawadtp@example.com",
                },
            ],
            "done": True,
        }

        results_insert_call = [
            {"id": "003000000000002", "success": True, "created": True},
            {"id": "003000000000003", "success": True, "created": True},
        ]

        step.sf.restful = mock.Mock(
            side_effect=[results_select_call, results_insert_call]
        )
        records = iter(
            [
                ["Jawad", "mjawadtp@example.com"],
                ["Aditya", "aditya@example.com"],
                ["Tom Cruise", "tom@example.com"],
            ]
        )
        step.start()
        step.select_records(records)
        step.end()

        # Get the results and assert their properties
        results = list(step.get_results())
        assert len(results) == 3  # Expect 3 results (matching the input records count)
        # Assert that all results have the expected ID, success, and created values
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000001", success=True, error="", created=False
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000002", success=True, error="", created=True
                )
            )
            == 1
        )
        assert (
            results.count(
                DataOperationResult(
                    id="003000000000003", success=True, error="", created=True
                )
            )
            == 1
        )

    @responses.activate
    def test_insert_dml_operation__boolean_conversion(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )

        recs = [
            ["Narvaez", "true"],
            ["Chalmers", "True"],
            ["De Vries", "False"],
            ["Aito", "false"],
            ["Boone", None],
            ["June", False],
            ["Zoom", True],
            ["Jewel", 0],
            ["Zule", 1],
            ["Jane", "0"],
            ["Zane", "1"],
        ]

        dml_op = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            context=task,
            api_options={},
            fields=["LastName", "IsEmailBounced"],
        )

        dml_op.start()
        dml_op.load_records(iter(recs))
        dml_op.end()

        assert json.loads(responses.calls[1].request.body) == {
            "allOrNone": False,
            "records": [
                {
                    "LastName": "Narvaez",
                    "IsEmailBounced": True,
                    "attributes": {"type": "Contact"},
                },
                {
                    "LastName": "Chalmers",
                    "IsEmailBounced": True,
                    "attributes": {"type": "Contact"},
                },
                {
                    "LastName": "De Vries",
                    "IsEmailBounced": False,
                    "attributes": {"type": "Contact"},
                },
                {
                    "LastName": "Aito",
                    "IsEmailBounced": False,
                    "attributes": {"type": "Contact"},
                },
                {
                    "LastName": "Boone",
                    "IsEmailBounced": False,
                    "attributes": {"type": "Contact"},
                },
                {
                    "LastName": "June",
                    "IsEmailBounced": False,
                    "attributes": {"type": "Contact"},
                },
                {
                    "LastName": "Zoom",
                    "IsEmailBounced": True,
                    "attributes": {"type": "Contact"},
                },
                {
                    "LastName": "Jewel",
                    "IsEmailBounced": False,
                    "attributes": {"type": "Contact"},
                },
                {
                    "LastName": "Zule",
                    "IsEmailBounced": True,
                    "attributes": {"type": "Contact"},
                },
                {
                    "LastName": "Jane",
                    "IsEmailBounced": False,
                    "attributes": {"type": "Contact"},
                },
                {
                    "LastName": "Zane",
                    "IsEmailBounced": True,
                    "attributes": {"type": "Contact"},
                },
            ],
        }

    @responses.activate
    def test_insert_dml_operation__boolean_conversion__fails(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )

        recs = [
            ["Narvaez", "xyzzy"],
        ]

        dml_op = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            context=task,
            api_options={},
            fields=["LastName", "IsEmailBounced"],
        )

        dml_op.start()
        with pytest.raises(BulkDataException) as e:
            dml_op.load_records(iter(recs))
        assert "xyzzy" in str(e.value)

    @responses.activate
    def test_insert_dml_operation__row_failure(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[
                {
                    "id": "003000000000003",
                    "success": False,
                    "errors": [
                        {
                            "statusCode": "VALIDATION_ERR",
                            "message": "Bad data",
                            "fields": ["FirstName"],
                        }
                    ],
                }
            ],
            status=200,
        )

        recs = [["Fred", "Narvaez"], [None, "De Vries"], ["Hiroko", "Aito"]]

        dml_op = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={"batch_size": 2},
            context=task,
            fields=["FirstName", "LastName"],
        )

        dml_op.start()
        dml_op.load_records(iter(recs))
        dml_op.end()

        assert dml_op.job_result == DataOperationJobResult(
            DataOperationStatus.ROW_FAILURE, [], 3, 1
        )
        assert list(dml_op.get_results()) == [
            DataOperationResult("003000000000001", True, "", True),
            DataOperationResult("003000000000002", True, "", True),
            DataOperationResult(
                "003000000000003", False, "VALIDATION_ERR: Bad data (FirstName)", True
            ),
        ]

    @responses.activate
    def test_insert_dml_operation__delete(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.DELETE,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects?ids=003000000000001,003000000000002",
            json=[
                {"id": "003000000000001", "success": True},
                {"id": "003000000000002", "success": True},
            ],
            status=200,
        )
        responses.add(
            responses.DELETE,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects?ids=003000000000003",
            json=[{"id": "003000000000003", "success": True}],
            status=200,
        )

        recs = [["003000000000001"], ["003000000000002"], ["003000000000003"]]

        dml_op = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.DELETE,
            api_options={"batch_size": 2},
            context=task,
            fields=["Id"],
        )

        dml_op.start()
        dml_op.load_records(iter(recs))
        dml_op.end()

        assert dml_op.job_result == DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 3, 0
        )
        assert list(dml_op.get_results()) == [
            DataOperationResult("003000000000001", True, ""),
            DataOperationResult("003000000000002", True, ""),
            DataOperationResult("003000000000003", True, ""),
        ]

    @responses.activate
    def test_insert_dml_operation__booleans(self):
        mock_describe_calls()
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite:///test.db",
                    "mapping": "mapping.yml",
                }
            },
        )
        task.project_config.project__package__api_version = CURRENT_SF_API_VERSION
        task._init_task()

        responses.add(
            responses.POST,
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            json=[{"id": "003000000000001", "success": True}],
            status=200,
        )

        recs = [["Narvaez", "True"]]
        dml_op = RestApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={"batch_size": 2},
            context=task,
            fields=["LastName", "IsEmailBounced"],  # IsEmailBounced is a Boolean field.
        )

        dml_op.start()
        dml_op.load_records(iter(recs))
        dml_op.end()

        json_body = json.loads(responses.calls[1].request.body)
        assert json_body["records"] == [
            {
                "LastName": "Narvaez",
                "IsEmailBounced": True,
                "attributes": {"type": "Contact"},
            }
        ]


class TestGetOperationFunctions:
    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiQueryOperation")
    def test_get_query_operation(self, rest_query, bulk_query):
        context = mock.Mock()
        context.sf.sf_version = "42.0"
        op = get_query_operation(
            sobject="Test",
            fields=["Id"],
            api_options={},
            context=context,
            query="SELECT Id FROM Test",
            api=DataApi.BULK,
        )
        assert op == bulk_query.return_value
        bulk_query.assert_called_once_with(
            sobject="Test",
            api_options={},
            context=context,
            query="SELECT Id FROM Test",
        )

        op = get_query_operation(
            sobject="Test",
            fields=["Id"],
            api_options={},
            context=context,
            query="SELECT Id FROM Test",
            api=DataApi.REST,
        )
        assert op == rest_query.return_value
        rest_query.assert_called_once_with(
            sobject="Test",
            fields=["Id"],
            api_options={},
            context=context,
            query="SELECT Id FROM Test",
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiQueryOperation")
    def test_get_query_operation__smart_to_rest(self, rest_query, bulk_query):
        context = mock.Mock()
        context.sf.restful.return_value = {"sObjects": [{"name": "Test", "count": 1}]}
        context.sf.sf_version = "42.0"
        op = get_query_operation(
            sobject="Test",
            fields=["Id"],
            api_options={},
            context=context,
            query="SELECT Id FROM Test",
            api=DataApi.SMART,
        )
        assert op == rest_query.return_value

        bulk_query.assert_not_called()
        context.sf.restful.assert_called_once_with("limits/recordCount?sObjects=Test")

    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiQueryOperation")
    def test_get_query_operation__smart_to_bulk(self, rest_query, bulk_query):
        context = mock.Mock()
        context.sf.restful.return_value = {
            "sObjects": [{"name": "Test", "count": 10000}]
        }
        context.sf.sf_version = "42.0"
        op = get_query_operation(
            sobject="Test",
            fields=["Id"],
            api_options={},
            context=context,
            query="SELECT Id FROM Test",
            api=DataApi.SMART,
        )
        assert op == bulk_query.return_value

        rest_query.assert_not_called()
        context.sf.restful.assert_called_once_with("limits/recordCount?sObjects=Test")

    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiQueryOperation")
    def test_get_query_operation__old_api_version(self, rest_query, bulk_query):
        context = mock.Mock()
        context.sf.sf_version = "39.0"
        op = get_query_operation(
            sobject="Test",
            fields=["Id"],
            api_options={},
            context=context,
            query="SELECT Id FROM Test",
            api=DataApi.SMART,
        )
        assert op == bulk_query.return_value

        context.sf.restful.assert_not_called()

    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiQueryOperation")
    def test_get_query_operation__bad_api(self, rest_query, bulk_query):
        context = mock.Mock()
        context.sf.sf_version = "42.0"
        with pytest.raises(AssertionError, match="Unknown API"):
            get_query_operation(
                sobject="Test",
                fields=["Id"],
                api_options={},
                context=context,
                query="SELECT Id FROM Test",
                api="foo",
            )

    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiQueryOperation")
    def test_get_query_operation__inferred_api(self, rest_query, bulk_query):
        context = mock.Mock()
        context.sf.sf_version = "42.0"
        context.sf.restful.return_value = {
            "sObjects": [{"name": "Test", "count": 10000}]
        }
        op = get_query_operation(
            sobject="Test",
            fields=["Id"],
            api_options={},
            context=context,
            query="SELECT Id FROM Test",
        )
        assert op == bulk_query.return_value

        context.sf.restful.assert_called_once_with("limits/recordCount?sObjects=Test")

    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiDmlOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiDmlOperation")
    def test_get_dml_operation(self, rest_dml, bulk_dml):
        context = mock.Mock()
        context.sf.sf_version = "42.0"
        op = get_dml_operation(
            sobject="Test",
            operation=DataOperationType.INSERT,
            fields=["Name"],
            api_options={},
            context=context,
            api=DataApi.BULK,
            volume=1,
            selection_strategy=SelectStrategy.SIMILARITY,
            selection_filter=None,
        )

        assert op == bulk_dml.return_value
        bulk_dml.assert_called_once_with(
            sobject="Test",
            operation=DataOperationType.INSERT,
            fields=["Name"],
            api_options={},
            context=context,
            selection_strategy=SelectStrategy.SIMILARITY,
            selection_filter=None,
            selection_priority_fields=None,
            content_type=None,
            threshold=None,
        )

        op = get_dml_operation(
            sobject="Test",
            operation=DataOperationType.INSERT,
            fields=["Name"],
            api_options={},
            context=context,
            api=DataApi.REST,
            volume=1,
            selection_strategy=SelectStrategy.SIMILARITY,
            selection_filter=None,
        )

        assert op == rest_dml.return_value
        rest_dml.assert_called_once_with(
            sobject="Test",
            operation=DataOperationType.INSERT,
            fields=["Name"],
            api_options={},
            context=context,
            selection_strategy=SelectStrategy.SIMILARITY,
            selection_filter=None,
            selection_priority_fields=None,
            content_type=None,
            threshold=None,
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiDmlOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiDmlOperation")
    def test_get_dml_operation__smart(self, rest_dml, bulk_dml):
        context = mock.Mock()
        context.sf.sf_version = "42.0"
        assert (
            get_dml_operation(
                sobject="Test",
                operation=DataOperationType.INSERT,
                fields=["Name"],
                api_options={},
                context=context,
                api=DataApi.SMART,
                volume=1,
            )
            == rest_dml.return_value
        )

        assert (
            get_dml_operation(
                sobject="Test",
                operation=DataOperationType.INSERT,
                fields=["Name"],
                api_options={},
                context=context,
                api=DataApi.SMART,
                volume=10000,
            )
            == bulk_dml.return_value
        )

        assert (
            get_dml_operation(
                sobject="Test",
                operation=DataOperationType.HARD_DELETE,
                fields=["Name"],
                api_options={},
                context=context,
                api=DataApi.SMART,
                volume=1,
            )
            == bulk_dml.return_value
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiDmlOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiDmlOperation")
    def test_get_dml_operation__inferred_api(self, rest_dml, bulk_dml):
        context = mock.Mock()
        context.sf.sf_version = "42.0"
        assert (
            get_dml_operation(
                sobject="Test",
                operation=DataOperationType.INSERT,
                fields=["Name"],
                api_options={},
                context=context,
                volume=1,
            )
            == rest_dml.return_value
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiDmlOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiDmlOperation")
    def test_get_dml_operation__old_api_version(self, rest_dml, bulk_dml):
        context = mock.Mock()
        context.sf.sf_version = "39.0"
        assert (
            get_dml_operation(
                sobject="Test",
                operation=DataOperationType.INSERT,
                fields=["Name"],
                api_options={},
                context=context,
                api=DataApi.SMART,
                volume=1,
            )
            == bulk_dml.return_value
        )

    @mock.patch("cumulusci.tasks.bulkdata.step.BulkApiDmlOperation")
    @mock.patch("cumulusci.tasks.bulkdata.step.RestApiDmlOperation")
    def test_get_dml_operation__bad_api(self, rest_dml, bulk_dml):
        context = mock.Mock()
        context.sf.sf_version = "42.0"
        with pytest.raises(AssertionError, match="Unknown API"):
            get_dml_operation(
                sobject="Test",
                operation=DataOperationType.INSERT,
                fields=["Name"],
                api_options={},
                context=context,
                api=42,
                volume=1,
            )

    def test_cleanup_date_strings__insert(self):
        """Empty date strings should be removed from INSERT operations"""
        context = mock.Mock()
        context.sf.sf_version = "42.0"
        context.sf.Test__c.describe = lambda: {
            "name": "Test__c",
            "fields": [
                {"name": "Birthdate", "type": "date"},
                {"name": "IsHappy", "type": "boolean"},
                {"name": "Name", "type": "string"},
            ],
        }

        step = get_dml_operation(
            sobject="Test__c",
            operation=DataOperationType.INSERT,
            fields=["Birthdate", "IsHappy", "Name"],
            api_options={},
            context=context,
            api=DataApi.REST,
            volume=1,
        )
        json_out = step._record_to_json(["", "", "Bill"])
        assert json_out == {
            "IsHappy": False,
            "Name": "Bill",
            "attributes": {"type": "Test__c"},
        }, json_out
        # Empty dates (and other fields) should be filtered out of INSERTs
        assert "BirthDate" not in json_out  # just for emphasis

    @pytest.mark.parametrize(
        "operation", ((DataOperationType.UPSERT, DataOperationType.UPDATE))
    )
    def test_cleanup_date_strings__upsert_update(self, operation):
        """Empty date strings should be NULLED for UPSERT and UPDATE operations"""
        context = mock.Mock()
        context.sf.sf_version = "42.0"
        context.sf.Test__c.describe = lambda: {
            "name": "Test__c",
            "fields": [
                {"name": "Birthdate", "type": "date"},
                {"name": "IsHappy", "type": "boolean"},
                {"name": "Name", "type": "string"},
            ],
        }

        step = get_dml_operation(
            sobject="Test__c",
            operation=operation,
            fields=["Birthdate", "IsHappy", "Name"],
            api_options={},
            context=context,
            api=DataApi.REST,
            volume=1,
        )
        # Empty dates (and other fields) should be NULLED in UPSERTs
        # Booleans become False for backwards-compatibility reasons.
        json_out = step._record_to_json(["", "", "Bill"])
        assert json_out == {
            "Birthdate": None,
            "IsHappy": False,
            "Name": "Bill",
            "attributes": {"type": "Test__c"},
        }, json_out


@pytest.mark.parametrize(
    "query_fields, expected",
    [
        # Test with simple field names
        (["Id", "Name", "Email"], ["Id", "Name", "Email"]),
        # Test with TYPEOF fields (polymorphic fields)
        (
            [
                "Subject",
                {
                    "Who": [
                        {"Contact": ["Name", "Email"]},
                        {"Lead": ["Name", "Company"]},
                    ]
                },
            ],
            [
                "Subject",
                "Who.Contact.Name",
                "Who.Contact.Email",
                "Who.Lead.Name",
                "Who.Lead.Company",
            ],
        ),
        # Test with mixed simple and TYPEOF fields
        (
            ["Subject", {"Who": [{"Contact": ["Email"]}]}, "Account.Name"],
            ["Subject", "Who.Contact.Email", "Account.Name"],
        ),
        # Test with an empty list
        ([], []),
    ],
)
def test_extract_flattened_headers(query_fields, expected):
    result = extract_flattened_headers(query_fields)
    assert result == expected


@pytest.mark.parametrize(
    "record, headers, expected",
    [
        # Test with simple field matching
        (
            {"Id": "001", "Name": "John Doe", "Email": "john@example.com"},
            ["Id", "Name", "Email"],
            ["001", "John Doe", "john@example.com"],
        ),
        # Test with lookup fields and missing values
        (
            {
                "Who": {
                    "attributes": {"type": "Contact"},
                    "Name": "Jane Doe",
                    "Email": "johndoe@org.com",
                    "Number": 10,
                }
            },
            ["Who.Contact.Name", "Who.Contact.Email", "Who.Contact.Number"],
            ["Jane Doe", "johndoe@org.com", "10"],
        ),
        # Test with non-matching ref_obj type
        (
            {"Who": {"attributes": {"type": "Contact"}, "Email": "jane@contact.com"}},
            ["Who.Lead.Email"],
            [""],
        ),
        # Test with mixed fields and nested lookups
        (
            {
                "Who": {"attributes": {"type": "Lead"}, "Name": "John Doe"},
                "Email": "john@example.com",
            },
            ["Who.Lead.Name", "Who.Lead.Company", "Email"],
            ["John Doe", "", "john@example.com"],
        ),
        # Test with mixed fields and nested lookups
        (
            {
                "Who": {"attributes": {"type": "Lead"}, "Name": "John Doe"},
                "Email": "john@example.com",
            },
            ["What.Account.Name"],
            [""],
        ),
        # Test with empty record
        ({}, ["Id", "Name"], ["", ""]),
    ],
)
def test_flatten_record(record, headers, expected):
    result = flatten_record(record, headers)
    assert result == expected


@pytest.mark.parametrize(
    "priority_fields, fields, expected",
    [
        # Test with priority fields matching
        (
            {"Id": "Id", "Name": "Name"},
            ["Id", "Name", "Email"],
            [HIGH_PRIORITY_VALUE, HIGH_PRIORITY_VALUE, LOW_PRIORITY_VALUE],
        ),
        # Test with no priority fields provided
        (None, ["Id", "Name", "Email"], [1, 1, 1]),
        # Test with empty priority fields dictionary
        ({}, ["Id", "Name", "Email"], [1, 1, 1]),
        # Test with some fields not in priority_fields
        (
            {"Id": "Id"},
            ["Id", "Name", "Email"],
            [HIGH_PRIORITY_VALUE, LOW_PRIORITY_VALUE, LOW_PRIORITY_VALUE],
        ),
    ],
)
def test_assign_weights(priority_fields, fields, expected):
    result = assign_weights(priority_fields, fields)
    assert result == expected
