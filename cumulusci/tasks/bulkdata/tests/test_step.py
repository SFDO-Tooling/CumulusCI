import io
import json
from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.bulkdata.step import (
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
    download_file,
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
            DataOperationResult("003000000000001", True, None),
            DataOperationResult("003000000000002", True, None),
            DataOperationResult(None, False, "error"),
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
            DataOperationResult("003000000000001", True, ""),
            DataOperationResult("003000000000002", True, ""),
            DataOperationResult("003000000000003", True, ""),
        ]

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
            DataOperationResult("003000000000001", True, ""),
            DataOperationResult("003000000000002", True, ""),
            DataOperationResult(
                "003000000000003", False, "VALIDATION_ERR: Bad data (FirstName)"
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

        context.sf.restful.called_once_with("limits/recordCount?sObjects=Test")

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
        )

        assert op == bulk_dml.return_value
        bulk_dml.assert_called_once_with(
            sobject="Test",
            operation=DataOperationType.INSERT,
            fields=["Name"],
            api_options={},
            context=context,
        )

        op = get_dml_operation(
            sobject="Test",
            operation=DataOperationType.INSERT,
            fields=["Name"],
            api_options={},
            context=context,
            api=DataApi.REST,
            volume=1,
        )

        assert op == rest_dml.return_value
        rest_dml.assert_called_once_with(
            sobject="Test",
            operation=DataOperationType.INSERT,
            fields=["Name"],
            api_options={},
            context=context,
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
