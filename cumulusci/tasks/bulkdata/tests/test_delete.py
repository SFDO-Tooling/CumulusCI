import unittest
from unittest import mock

from cumulusci.tasks.bulkdata import DeleteData
from cumulusci.tasks.bulkdata.step import Status, Result, Operation
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.core.exceptions import TaskOptionsError, BulkDataException


class TestDeleteData(unittest.TestCase):
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryStep")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlStep")
    def test_run(self, dml_mock, query_mock):
        task = _make_task(DeleteData, {"options": {"objects": "Contact"}})
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.status = Status.SUCCESS
        dml_mock.return_value.get_results.return_value = iter(
            [
                Result("001000000000000", True, None),
                Result("001000000000001", True, None),
            ]
        )
        task()

        query_mock.assert_called_once_with(
            "Contact", {}, task, "SELECT Id FROM Contact"
        )
        query_mock.return_value.query.assert_called_once()
        query_mock.return_value.get_results.assert_called_once()

        dml_mock.assert_called_once_with("Contact", Operation.DELETE, {}, task, ["Id"])
        dml_mock.return_value.start.assert_called_once()
        dml_mock.return_value.end.assert_called_once()
        dml_mock.return_value.load_records.assert_called_once()
        dml_mock.return_value.get_results.assert_called_once()

    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryStep")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlStep")
    def test_run__error(self, dml_mock, query_mock):
        task = _make_task(DeleteData, {"options": {"objects": "Contact"}})
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.status = Status.SUCCESS
        dml_mock.return_value.get_results.return_value = iter(
            [
                Result("001000000000000", True, None),
                Result("001000000000001", False, None),
            ]
        )
        with self.assertRaises(BulkDataException):
            task()

    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryStep")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlStep")
    def test_run__ignore_error(self, dml_mock, query_mock):
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
        query_mock.return_value.status = Status.SUCCESS
        dml_mock.return_value.get_results.return_value = iter(
            [
                Result("001000000000000", True, None),
                Result("001000000000001", False, None),
            ]
        )
        task()
        query_mock.assert_called_once_with(
            "Contact", {}, task, "SELECT Id FROM Contact"
        )
        query_mock.return_value.query.assert_called_once()
        query_mock.return_value.get_results.assert_called_once()

        dml_mock.assert_called_once_with(
            "Contact", Operation.HARD_DELETE, {}, task, ["Id"]
        )
        dml_mock.return_value.start.assert_called_once()
        dml_mock.return_value.end.assert_called_once()
        dml_mock.return_value.load_records.assert_called_once()
        dml_mock.return_value.get_results.assert_called_once()

    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryStep")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlStep")
    def test_run__where(self, dml_mock, query_mock):
        task = _make_task(
            DeleteData, {"options": {"objects": "Contact", "where": "Id != null"}}
        )
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.status = Status.SUCCESS
        dml_mock.return_value.get_results.return_value = iter(
            [
                Result("001000000000000", True, None),
                Result("001000000000001", True, None),
            ]
        )
        task()
        query_mock.assert_called_once_with(
            "Contact", {}, task, "SELECT Id FROM Contact WHERE Id != null"
        )
        query_mock.return_value.query.assert_called_once()
        query_mock.return_value.get_results.assert_called_once()

        dml_mock.assert_called_once_with("Contact", Operation.DELETE, {}, task, ["Id"])
        dml_mock.return_value.start.assert_called_once()
        dml_mock.return_value.end.assert_called_once()
        dml_mock.return_value.load_records.assert_called_once()
        dml_mock.return_value.get_results.assert_called_once()

    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiQueryStep")
    @mock.patch("cumulusci.tasks.bulkdata.delete.BulkApiDmlStep")
    def test_run__query_fails(self, dml_mock, query_mock):
        task = _make_task(
            DeleteData, {"options": {"objects": "Contact", "where": "Id != null"}}
        )
        query_mock.return_value.get_results.return_value = iter(
            ["001000000000000", "001000000000001"]
        )
        query_mock.return_value.status = Status.FAILURE
        with self.assertRaises(BulkDataException):
            task()

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
