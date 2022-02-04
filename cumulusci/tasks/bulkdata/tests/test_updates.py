from functools import wraps
from unittest import mock
from unittest.mock import call

import pytest

from cumulusci.core import exceptions as exc
from cumulusci.tasks.bulkdata.step import (
    DataApi,
    DataOperationJobResult,
    DataOperationResult,
    DataOperationStatus,
    DataOperationType,
)
from cumulusci.tasks.bulkdata.update_data import UpdateData


def _hashify_operation(kwargs):
    return frozenset(
        {
            **kwargs,
            "context": None,
            "fields": frozenset(kwargs["fields"]),
            "api_options": frozenset(kwargs.get("api_options", {}).items()),
        }.items()
    )


def noop(*args, **kwargs):
    pass


class MockBulkAPIResponses:
    def activate(self, func):
        @wraps(func)
        def wrapper(*args, **kwds):
            self.mock_bulk_API_responses_context = MockBulkAPIResponsesContext()
            with mock.patch(
                "cumulusci.tasks.bulkdata.update_data.get_query_operation",
                self.mock_bulk_API_responses_context.get_query_operation,
            ), mock.patch(
                "cumulusci.tasks.bulkdata.update_data.get_dml_operation",
                self.mock_bulk_API_responses_context.get_dml_operation,
            ):
                try:
                    ret = func(*args, **kwds)
                finally:
                    self.mock_bulk_API_responses_context = None
            return ret

        return wrapper

    @property
    def add_query_operation(self):
        return self.mock_bulk_API_responses_context.add_query_operation

    @property
    def add_dml_operation(self):
        return self.mock_bulk_API_responses_context.add_dml_operation


class MockBulkAPIResponsesContext:
    def __init__(self):
        self.query_operations = {}
        self.dml_operations = {}

    def add_query_operation(self, *, results, **expected):
        self.query_operations[_hashify_operation(expected)] = results

    def add_dml_operation(self, *, results, loader_callback=noop, **expected):
        self.dml_operations[_hashify_operation(expected)] = [loader_callback, results]

    def get_query_operation(self, **given):
        try:
            results = self.query_operations[_hashify_operation(given)]
        except KeyError:
            raise KeyError(f"Cannot find response matching {given}")
        return FakeOperationResult(results)

    def get_dml_operation(self, **given):
        try:
            loader_callback, results = self.dml_operations[_hashify_operation(given)]
        except KeyError:
            raise KeyError(f"Cannot find response matching {given}")
        return FakeDMLOperationResult(
            results, fields=given["fields"], loader_callback=loader_callback
        )


class FakeOperationResult:
    def __init__(self, results, numrecords=None):
        self.results = results
        if numrecords is None:
            numrecords = len(self.results)
        self.numrecords = numrecords

    def yield_per(self, number):  # TODO
        return self.results

    def count(self):
        return self.numrecords

    def query(self):
        pass

    @property
    def job_result(self):
        return DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], len(self.results), 0
        )

    def get_results(self):
        return self.results


class FakeDMLOperationResult(FakeOperationResult):
    def __init__(self, results, numrecords=None, loader_callback=noop, fields=None):
        self.results = results
        if numrecords is None:
            numrecords = len(self.results)
        self.numrecords = numrecords
        self.loader_callback = loader_callback
        self.fields = fields

    def start(self):
        pass

    def load_records(self, records, *args, **kwargs):
        for record in records:
            self.loader_callback(dict(zip(self.fields, record)))

    def end(self):
        pass


def _fake_validate_and_inject_namespace_prefixes(
    should_inject_namespaces: bool,
    sobjects_to_validate: list,
    operation_to_validate: str,
):
    return sobjects_to_validate


bulkapi_responses = MockBulkAPIResponses()


class TestUpdates:
    def test_options__bad_sobject(self, create_task):
        with pytest.raises(exc.TaskOptionsError) as e:
            task = create_task(UpdateData, {"object": "a b c"})
            task()
        assert "a b c" in str(e.value), e.value

    def test_options__bad_field(self, create_task):
        with pytest.raises(exc.TaskOptionsError) as e:
            task = create_task(UpdateData, {"object": "Account", "fields": ["a b c"]})
            task()
        assert "a b c" in str(e.value), e.value

    def test_options__bad_fields(self, create_task):
        with pytest.raises(exc.TaskOptionsError) as e:
            task = create_task(
                UpdateData, {"object": "Account", "fields": ["a b c", "1 2 3"]}
            )
            task()
        assert "a b c" in str(e.value), e.value

    def test_options__bad_api(self, create_task):
        with pytest.raises(exc.TaskOptionsError) as e:
            task = create_task(UpdateData, {"object": "Account", "api": "XML-RPC"})
            task()
        assert "XML-RPC" in str(e.value), e.value

    @bulkapi_responses.activate
    def test_with_fake_query_results(self, create_task):

        bulkapi_responses.add_query_operation(
            sobject="Account",
            fields=["Id", "Name"],
            query="SELECT Id,Name FROM Account",
            api=DataApi.SMART,
            results=[
                ["OID000BLAH", "Mark Benihoff"],
                ["OID000BLAH2", "Parkour Hairish"],
            ],
        )
        loader = mock.Mock()
        bulkapi_responses.add_dml_operation(
            sobject="Account",
            operation=DataOperationType.UPDATE,
            fields=["BillingStreet", "Description", "NumberOfEmployees", "Id"],
            api_options={},
            api=DataApi.SMART,
            volume=2,
            results=[DataOperationResult("00OIDXYZ", success=True, error="")],
            loader_callback=loader,
        )

        task = create_task(
            UpdateData,
            {
                "object": "Account",
                "recipe": "datasets/update.recipe.yml",
                "fields": ["Name"],
            },
        )

        task._validate_and_inject_namespace_prefixes = (
            _fake_validate_and_inject_namespace_prefixes
        )
        task()
        assert loader.mock_calls == [
            call(
                {
                    "BillingStreet": mock.ANY,
                    "Description": "Mark Benihoff is our favorite customer",
                    "NumberOfEmployees": "10000",
                    "Id": "OID000BLAH",
                }
            ),
            call(
                {
                    "BillingStreet": mock.ANY,
                    "Description": "Parkour Hairish is our favorite customer",
                    "NumberOfEmployees": "10000",
                    "Id": "OID000BLAH2",
                }
            ),
        ]

    @bulkapi_responses.activate
    def test_with_no_query_results(self, create_task):
        bulkapi_responses.add_query_operation(
            sobject="Account",
            fields=["Id", "Name"],
            query="SELECT Id,Name FROM Account",
            api=DataApi.SMART,
            results=[],
        )

        task = create_task(
            UpdateData,
            {
                "object": "Account",
                "recipe": "datasets/update.recipe.yml",
                "fields": ["Name"],
            },
        )

        task._validate_and_inject_namespace_prefixes = (
            _fake_validate_and_inject_namespace_prefixes
        )
        task.logger = mock.Mock()
        task()
        assert (
            task.logger.mock_calls[-1].args[0].startswith("No records found")
        ), task.logger.mock_calls[-1].args[0]
