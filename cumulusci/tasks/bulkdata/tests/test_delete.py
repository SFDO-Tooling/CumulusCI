import pytest
import unittest
from unittest import mock

import responses

from cumulusci.core.exceptions import TaskOptionsError, BulkDataException
from cumulusci.tasks.bulkdata import DeleteData
from cumulusci.tasks.bulkdata.step import (
    DataOperationStatus,
    DataOperationResult,
    DataOperationJobResult,
    DataOperationType,
)
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.tasks.bulkdata.tests.test_utils import mock_describe_calls


class TestDeleteData(unittest.TestCase):
    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlOperation")
    def test_run(self, dml_mock, query_mock):
        mock_describe_calls()
        task = _make_task(DeleteData, {"options": {"objects": "Contact"}})
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        dml_mock.return_value.get_results.return_value = iter(
            [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("001000000000001", True, None),
            ]
        )
        dml_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        task()

        query_mock.assert_called_once_with(
            sobject="Contact",
            api_options={},
            context=task,
            query="SELECT Id FROM Contact",
        )
        query_mock.return_value.query.assert_called_once()
        query_mock.return_value.get_results.assert_called_once()

        dml_mock.assert_called_once_with(
            sobject="Contact",
            operation=DataOperationType.DELETE,
            api_options={},
            context=task,
            fields=["Id"],
        )
        dml_mock.return_value.start.assert_called_once()
        dml_mock.return_value.end.assert_called_once()
        dml_mock.return_value.load_records.assert_called_once()
        dml_mock.return_value.get_results.assert_called_once()

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlOperation")
    def test_run__no_results(self, dml_mock, query_mock):
        mock_describe_calls()
        task = _make_task(DeleteData, {"options": {"objects": "Contact"}})
        query_mock.return_value.get_results.return_value = iter([])
        query_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        task()

        query_mock.assert_called_once_with(
            sobject="Contact",
            api_options={},
            context=task,
            query="SELECT Id FROM Contact",
        )
        query_mock.return_value.query.assert_called_once()
        query_mock.return_value.get_results.assert_not_called()

        dml_mock.assert_not_called()

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlOperation")
    def test_run__job_error_delete(self, dml_mock, query_mock):
        mock_describe_calls()
        task = _make_task(DeleteData, {"options": {"objects": "Contact"}})
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        dml_mock.return_value.get_results.return_value = iter(
            [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("001000000000001", False, None),
            ]
        )
        with self.assertRaises(BulkDataException):
            task()

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlOperation")
    def test_run__job_error_query(self, dml_mock, query_mock):
        mock_describe_calls()
        task = _make_task(DeleteData, {"options": {"objects": "Contact"}})
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.JOB_FAILURE, [], 0, 0
        )
        with self.assertRaises(BulkDataException):
            task()

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlOperation")
    def test_run__row_error(self, dml_mock, query_mock):
        mock_describe_calls()
        task = _make_task(DeleteData, {"options": {"objects": "Contact"}})
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        dml_mock.return_value.get_results.return_value = iter(
            [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("001000000000001", False, None),
            ]
        )
        with self.assertRaises(BulkDataException):
            task()

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlOperation")
    def test_run__ignore_error(self, dml_mock, query_mock):
        mock_describe_calls()
        task = _make_task(
            DeleteData,
            {
                "options": {
                    "objects": "Contact",
                    "ignore_row_errors": "true",
                    "hardDelete": "true",
                }
            },
        )
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        dml_mock.return_value.get_results.return_value = iter(
            [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("001000000000001", False, None),
            ]
        )
        dml_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        with mock.patch.object(task.logger, "warning") as warning:
            task()
        assert len(warning.mock_calls) == 1
        query_mock.assert_called_once_with(
            sobject="Contact",
            api_options={},
            context=task,
            query="SELECT Id FROM Contact",
        )
        query_mock.return_value.query.assert_called_once()
        query_mock.return_value.get_results.assert_called_once()

        dml_mock.assert_called_once_with(
            sobject="Contact",
            operation=DataOperationType.HARD_DELETE,
            api_options={},
            context=task,
            fields=["Id"],
        )
        dml_mock.return_value.start.assert_called_once()
        dml_mock.return_value.end.assert_called_once()
        dml_mock.return_value.load_records.assert_called_once()
        dml_mock.return_value.get_results.assert_called_once()

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlOperation")
    def test_run__ignore_error_throttling(self, dml_mock, query_mock):
        mock_describe_calls()
        task = _make_task(
            DeleteData,
            {
                "options": {
                    "objects": "Contact",
                    "ignore_row_errors": "true",
                    "hardDelete": "true",
                }
            },
        )
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"] * 15
        )
        query_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        dml_mock.return_value.get_results.return_value = iter(
            [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("001000000000001", False, None),
            ]
            * 15
        )
        dml_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        with mock.patch.object(task.logger, "warning") as warning:
            task()
        assert len(warning.mock_calls) == task.row_warning_limit + 1 == 11
        assert "warnings suppressed" in str(warning.mock_calls[-1])

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlOperation")
    def test_run__where(self, dml_mock, query_mock):
        mock_describe_calls()
        task = _make_task(
            DeleteData, {"options": {"objects": "Contact", "where": "Id != null"}}
        )
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        dml_mock.return_value.get_results.return_value = iter(
            [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("001000000000001", True, None),
            ]
        )
        dml_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 2, 0
        )
        task()
        query_mock.assert_called_once_with(
            sobject="Contact",
            api_options={},
            context=task,
            query="SELECT Id FROM Contact WHERE Id != null",
        )
        query_mock.return_value.query.assert_called_once()
        query_mock.return_value.get_results.assert_called_once()

        dml_mock.assert_called_once_with(
            sobject="Contact",
            operation=DataOperationType.DELETE,
            api_options={},
            context=task,
            fields=["Id"],
        )
        dml_mock.return_value.start.assert_called_once()
        dml_mock.return_value.end.assert_called_once()
        dml_mock.return_value.load_records.assert_called_once()
        dml_mock.return_value.get_results.assert_called_once()

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryOperation")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlOperation")
    def test_run__query_fails(self, dml_mock, query_mock):
        mock_describe_calls()
        task = _make_task(
            DeleteData, {"options": {"objects": "Contact", "where": "Id != null"}}
        )
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.JOB_FAILURE, [], 0, 0
        )
        with self.assertRaises(BulkDataException):
            task()

    @responses.activate
    def test_validate_and_inject_namespace__standard(self):
        mock_describe_calls()

        task = _make_task(DeleteData, {"options": {"objects": "Contact,Account"}})

        task._validate_and_inject_namespace()

        assert task.sobjects == ["Contact", "Account"]

    @responses.activate
    def test_validate_and_inject_namespace__missing_object(self):
        mock_describe_calls()
        task = _make_task(
            DeleteData, {"options": {"objects": "ApexTestQueueItem,Account"}}
        )
        # ApexTestQueueItem is not deletable

        with pytest.raises(BulkDataException):
            task._validate_and_inject_namespace()

    def test_validate_and_inject_namespace__packaged(self):
        task = _make_task(DeleteData, {"options": {"objects": "Contact,Test__c"}})
        task.project_config.project__package__namespace = "ns"
        task.org_config = mock.Mock()
        task.org_config.salesforce_client.describe.return_value = {
            "sobjects": [
                {"name": "ns__Test__c", "deletable": True},
                {"name": "Contact", "deletable": True},
            ]
        }

        task._validate_and_inject_namespace()

        assert task.sobjects == ["Contact", "ns__Test__c"]

    def test_validate_and_inject_namespace__packaged_and_not(self):
        task = _make_task(DeleteData, {"options": {"objects": "Contact,Test__c"}})
        task.project_config.project__package__namespace = "ns"
        task.org_config = mock.Mock()
        task.org_config.salesforce_client.describe.return_value = {
            "sobjects": [
                {"name": "Test__c", "deletable": True},
                {"name": "Contact", "deletable": True},
                {"name": "ns__Test__c", "deletable": True},
            ]
        }

        task._validate_and_inject_namespace()

        # Prefer the user entry where there is ambiguity.
        assert task.sobjects == ["Contact", "Test__c"]

    def test_object_description(self):
        t = _make_task(DeleteData, {"options": {"objects": "a", "where": "Id != null"}})
        assert t._object_description("a") == 'a objects matching "Id != null"'

        t = _make_task(DeleteData, {"options": {"objects": "a"}})
        assert t._object_description("a") == "all a objects"

    def test_init_options(self):
        with self.assertRaises(TaskOptionsError):
            _make_task(DeleteData, {"options": {"objects": ""}})

        with self.assertRaises(TaskOptionsError):
            _make_task(DeleteData, {"options": {"objects": "a,b", "where": "x='y'"}})

        t = _make_task(
            DeleteData,
            {
                "options": {
                    "objects": "a",
                    "where": "Id != null",
                    "hardDelete": "true",
                    "ignore_row_errors": "false",
                }
            },
        )
        assert t.options["where"] == "Id != null"
        assert not t.options["ignore_row_errors"]
        assert t.options["hardDelete"]

        t = _make_task(DeleteData, {"options": {"objects": "a,b"}})
        assert t.options["objects"] == ["a", "b"]
