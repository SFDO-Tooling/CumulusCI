import typing as T
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
from cumulusci.tasks.bulkdata.tests.integration_test_utils import ensure_accounts
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


ensure_accounts = ensure_accounts  # cleans up multiple lint errors at once.


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


class FakeJobOperationResults(T.NamedTuple):
    results: list
    job_result_status: DataOperationStatus
    loader_callback: T.Callable = noop


class MockBulkAPIResponsesContext:
    def __init__(self):
        self.query_operations = {}
        self.dml_operations = {}

    def add_query_operation(
        self, *, results, job_result_status=DataOperationStatus.SUCCESS, **expected
    ):
        self.query_operations[_hashify_operation(expected)] = FakeJobOperationResults(
            results,
            job_result_status,
        )

    def add_dml_operation(
        self,
        *,
        results,
        loader_callback=noop,
        job_result_status=DataOperationStatus.SUCCESS,
        **expected,
    ):
        val = FakeJobOperationResults(results, job_result_status, loader_callback)
        self.dml_operations[_hashify_operation(expected)] = val

    def get_query_operation(self, **given):
        try:
            results = self.query_operations[_hashify_operation(given)]
        except KeyError:
            raise KeyError(f"Cannot find response matching {given}")
        return FakeOperationResult(results)

    def get_dml_operation(self, **given):
        try:
            results = self.dml_operations[_hashify_operation(given)]
        except KeyError:
            raise KeyError(f"Cannot find response matching {given}")
        return FakeDMLOperationResult(results, fields=given["fields"])


class FakeOperationResult:
    def __init__(self, results: FakeJobOperationResults):
        self.results = results

    def yield_per(self, number):  # TODO
        return self.results.results

    def count(self):
        return len(self.results.results)

    def query(self):
        pass

    @property
    def job_result(self):
        return DataOperationJobResult(
            self.results.job_result_status, [], len(self.results.results), 0
        )

    def get_results(self):
        return self.results.results


class FakeDMLOperationResult(FakeOperationResult):
    def __init__(self, results: FakeJobOperationResults, fields=None):
        self.results = results
        self.fields = fields

    def start(self):
        pass

    def load_records(self, records, *args, **kwargs):
        for record in records:
            self.results.loader_callback(dict(zip(self.fields, record)))

    def end(self):
        pass

    @property
    def job_result(self):
        return DataOperationJobResult(
            self.results.job_result_status,
            [],
            len(self.results.results),
            sum(1 for r in self.results.results if r.success is False),
        )


def _fake_val_and_inject_ns(
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
    def test_simple_task(self, create_task):

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
            results=[
                DataOperationResult("OID000BLAH", success=True, error=""),
                DataOperationResult("OID000BLAH2", success=True, error=""),
            ],
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

        task._validate_and_inject_namespace_prefixes = _fake_val_and_inject_ns
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
        ], loader.mock_calls

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

        task._validate_and_inject_namespace_prefixes = _fake_val_and_inject_ns
        task.logger = mock.Mock()
        task()
        last_message = task.logger.mock_calls[-1].args[0]
        assert last_message.startswith("No records found"), last_message

    @bulkapi_responses.activate
    def test_with_where_clause(self, create_task):
        bulkapi_responses.add_query_operation(
            sobject="Account",
            fields=["Id", "Name"],
            query="SELECT Id,Name FROM Account WHERE name LIKE '%ark%'",
            api=DataApi.SMART,
            results=[
                ["OID000BLAH", "Mark Benihoff"],
                ["OID000BLAH2", "Parkour Hairish"],
            ],
        )
        bulkapi_responses.add_dml_operation(
            sobject="Account",
            operation=DataOperationType.UPDATE,
            fields=["BillingStreet", "Description", "NumberOfEmployees", "Id"],
            api_options={},
            api=DataApi.SMART,
            volume=2,
            results=[
                DataOperationResult("OID000BLAH", success=True, error=""),
                DataOperationResult("OID000BLAH2", success=True, error=""),
            ],
        )
        task = create_task(
            UpdateData,
            {
                "object": "Account",
                "recipe": "datasets/update.recipe.yml",
                "fields": ["Name"],
                "where": "name LIKE '%ark%'",
            },
        )
        task._validate_and_inject_namespace_prefixes = _fake_val_and_inject_ns
        task.logger = mock.Mock()
        task()
        last_message = task.logger.mock_calls[-1].args[0]
        assert last_message.startswith(
            "Account objects matching \"name like '%ark%'\""
        ), last_message

    @bulkapi_responses.activate
    def test_query_failed(self, create_task):
        bulkapi_responses.add_query_operation(
            sobject="Account",
            fields=["Id", "Name"],
            query="SELECT Id,Name FROM Account",
            api=DataApi.SMART,
            results=[],
            job_result_status=DataOperationStatus.JOB_FAILURE,
        )
        loader = mock.Mock()
        bulkapi_responses.add_dml_operation(
            sobject="Account",
            operation=DataOperationType.UPDATE,
            fields=["BillingStreet", "Description", "NumberOfEmployees", "Id"],
            api_options={},
            api=DataApi.SMART,
            volume=2,
            results=[
                DataOperationResult("OID000BLAH", success=True, error=""),
                DataOperationResult("OID000BLAH2", success=True, error=""),
            ],
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

        task._validate_and_inject_namespace_prefixes = _fake_val_and_inject_ns
        with pytest.raises(exc.BulkDataException) as e:
            task()

        assert "Unable to query records" in str(e.value)
        assert "Account" in str(e.value)

    @bulkapi_responses.activate
    def test_update_query_failed(self, create_task):
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
            results=[],
            loader_callback=loader,
            job_result_status=DataOperationStatus.JOB_FAILURE,
        )

        task = create_task(
            UpdateData,
            {
                "object": "Account",
                "recipe": "datasets/update.recipe.yml",
                "fields": ["Name"],
            },
        )

        task._validate_and_inject_namespace_prefixes = _fake_val_and_inject_ns
        with pytest.raises(exc.BulkDataException) as e:
            task()
        assert "Unable to update records" in str(e.value)

    @bulkapi_responses.activate
    def test_update_row_errors(self, create_task):
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
            results=[
                DataOperationResult("OID000BEEF", success=True, error=""),
                DataOperationResult("OID000BLAH", success=False, error="humbug"),
            ],
            loader_callback=loader,
            job_result_status=DataOperationStatus.ROW_FAILURE,
        )

        task = create_task(
            UpdateData,
            {
                "object": "Account",
                "recipe": "datasets/update.recipe.yml",
                "fields": ["Name"],
                "ignore_row_errors": True,
            },
        )

        task._validate_and_inject_namespace_prefixes = _fake_val_and_inject_ns
        task.logger = mock.Mock()
        task()
        assert task.return_values["status"] == DataOperationStatus.ROW_FAILURE
        assert task.return_values["total_row_errors"] == 1
        assert (
            task.logger.mock_calls[-1].args[0]
            == "All account objects processed (2). 1 errors"
        ), task.logger.mock_calls[-1].args[0]

    @bulkapi_responses.activate
    def test_update_row_errors_exception_catching(self, create_task):
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
            results=[
                DataOperationResult("OID000BEEF", success=True, error=""),
                DataOperationResult("OID000BLAH", success=False, error="humbug"),
            ],
            loader_callback=loader,
            job_result_status=DataOperationStatus.ROW_FAILURE,
        )

        task = create_task(
            UpdateData,
            {
                "object": "Account",
                "recipe": "datasets/update.recipe.yml",
                "fields": ["Name"],
                "ignore_row_errors": False,
            },
        )

        task._validate_and_inject_namespace_prefixes = _fake_val_and_inject_ns
        with pytest.raises(exc.BulkDataException) as e:
            task()
        assert str(e.value) == "1 update error"


class TestUpdatesIntegrationTests:

    # VCR doesn't match because of randomized data
    @pytest.mark.vcr()
    def test_updates_task(self, create_task, ensure_accounts):
        with ensure_accounts(6):
            task = create_task(
                UpdateData,
                {
                    "object": "Account",
                    "recipe": "datasets/update.recipe.yml",
                    "fields": ["Name"],
                },
            )
            task.logger = mock.Mock()
            task()
            last_message = task.logger.mock_calls[-1].args[0]
            assert (
                str(last_message) == "All account objects successfully updated (6)."
            ), str(last_message)
