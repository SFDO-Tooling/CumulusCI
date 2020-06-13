from collections import OrderedDict
from datetime import datetime
import os
import json
import shutil
import unittest
from unittest import mock

import responses
from sqlalchemy import Column, Table, Unicode

from cumulusci.core.exceptions import BulkDataException, TaskOptionsError
from cumulusci.tasks.bulkdata import LoadData
from cumulusci.tasks.bulkdata.step import (
    DataOperationResult,
    DataOperationJobResult,
    DataOperationType,
    DataOperationStatus,
    BaseDmlOperation,
)
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.utils import temporary_dir
from cumulusci.tasks.bulkdata.mapping_parser import MappingLookup, MappingStep


class MockBulkApiDmlOperation(BaseDmlOperation):
    def __init__(
        self, *, context, sobject=None, operation=None, api_options=None, fields=None,
    ):
        super().__init__(
            sobject=sobject,
            operation=operation,
            api_options=api_options,
            context=context,
            fields=fields,
        )
        self._results = []
        self.records = []

    def start(self):
        self.job_id = "JOB"

    def end(self):
        records_processed = len(self.results)
        self.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], records_processed, 0
        )

    def load_records(self, records):
        self.records.extend(records)

    def get_results(self):
        return iter(self.results)

    @property
    def results(self):
        return self._results

    @results.setter
    def results(self, results):
        self._results = results
        self.end()


class TestLoadData(unittest.TestCase):
    mapping_file = "mapping_v1.yml"

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.load.BulkApiDmlOperation")
    def test_run(self, step_mock):
        responses.add(
            method="GET",
            url="https://example.com/services/data/v46.0/query/?q=SELECT+Id+FROM+RecordType+WHERE+SObjectType%3D%27Account%27AND+DeveloperName+%3D+%27HH_Account%27+LIMIT+1",
            body=json.dumps({"records": [{"Id": "1"}]}),
            status=200,
        )

        base_path = os.path.dirname(__file__)
        db_path = os.path.join(base_path, "testdata.db")
        mapping_path = os.path.join(base_path, self.mapping_file)

        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "testdata.db")
            shutil.copyfile(db_path, tmp_db_path)

            task = _make_task(
                LoadData,
                {
                    "options": {
                        "database_url": f"sqlite:///{tmp_db_path}",
                        "mapping": mapping_path,
                    }
                },
            )

            task.bulk = mock.Mock()
            task.sf = mock.Mock()

            step = MockBulkApiDmlOperation(
                sobject="Contact",
                operation=DataOperationType.INSERT,
                api_options={},
                context=task,
                fields=[],
            )
            step_mock.return_value = step

            step.results = [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("003000000000000", True, None),
                DataOperationResult("003000000000001", True, None),
            ]

            task()

            assert step.records == [
                ["TestHousehold", "1"],
                ["Test", "User", "test@example.com", "001000000000000"],
                ["Error", "User", "error@example.com", "001000000000000"],
            ]

            hh_ids = task.session.query(
                *task.metadata.tables["households_sf_ids"].columns
            ).one()
            assert hh_ids == ("1", "001000000000000")

            task.session.close()
            task.engine.dispose()

    def test_run_task__start_step(self):
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite://",
                    "mapping": "mapping.yml",
                    "start_step": "Insert Contacts",
                }
            },
        )
        task._init_db = mock.Mock()
        task._init_mapping = mock.Mock()
        task.mapping = {}
        task.mapping["Insert Households"] = MappingStep(sf_object="one", fields={})
        task.mapping["Insert Contacts"] = MappingStep(sf_object="two", fields={})
        task.after_steps = {}
        task._execute_step = mock.Mock(
            return_value=DataOperationJobResult(DataOperationStatus.SUCCESS, [], 0, 0)
        )
        task()
        task._execute_step.assert_called_once_with(
            MappingStep(sf_object="two", fields={})
        )

    def test_run_task__after_steps(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )
        task._init_db = mock.Mock()
        task._init_mapping = mock.Mock()
        task._expand_mapping = mock.Mock()
        task.mapping = {}
        task.mapping["Insert Households"] = 1
        task.mapping["Insert Contacts"] = 2
        households_steps = {}
        households_steps["four"] = 4
        households_steps["five"] = 5
        task.after_steps = {
            "Insert Contacts": {"three": 3},
            "Insert Households": households_steps,
        }
        task._execute_step = mock.Mock(
            return_value=DataOperationJobResult(DataOperationStatus.SUCCESS, [], 0, 0)
        )
        task()
        task._execute_step.assert_has_calls(
            [mock.call(1), mock.call(4), mock.call(5), mock.call(2), mock.call(3)]
        )

    def test_run_task__after_steps_failure(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )
        task._init_db = mock.Mock()
        task._init_mapping = mock.Mock()
        task._expand_mapping = mock.Mock()
        task.mapping = {}
        task.mapping["Insert Households"] = 1
        task.mapping["Insert Contacts"] = 2
        households_steps = {}
        households_steps["four"] = 4
        households_steps["five"] = 5
        task.after_steps = {
            "Insert Contacts": {"three": 3},
            "Insert Households": households_steps,
        }
        task._execute_step = mock.Mock(
            side_effect=[
                DataOperationJobResult(DataOperationStatus.SUCCESS, [], 0, 0),
                DataOperationJobResult(DataOperationStatus.JOB_FAILURE, [], 0, 0),
            ]
        )
        with self.assertRaises(BulkDataException):
            task()

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.load.BulkApiDmlOperation")
    def test_run__sql(self, step_mock):
        responses.add(
            method="GET",
            url="https://example.com/services/data/v46.0/query/?q=SELECT+Id+FROM+RecordType+WHERE+SObjectType%3D%27Account%27AND+DeveloperName+%3D+%27HH_Account%27+LIMIT+1",
            body=json.dumps({"records": [{"Id": "1"}]}),
            status=200,
        )

        base_path = os.path.dirname(__file__)
        sql_path = os.path.join(base_path, "testdata.sql")
        mapping_path = os.path.join(base_path, self.mapping_file)

        task = _make_task(
            LoadData, {"options": {"sql_path": sql_path, "mapping": mapping_path}}
        )
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        step = MockBulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step_mock.return_value = step
        step.results = [
            DataOperationResult("001000000000000", True, None),
            DataOperationResult("003000000000000", True, None),
            DataOperationResult("003000000000001", True, None),
        ]
        task()

        assert step.records == [
            ["TestHousehold", "1"],
            ["Test", "User", "test@example.com", "001000000000000"],
            ["Error", "User", "error@example.com", "001000000000000"],
        ]

        hh_ids = task.session.query(
            *task.metadata.tables["households_sf_ids"].columns
        ).one()
        assert hh_ids == ("1", "001000000000000")

    def test_init_options__missing_input(self):
        with self.assertRaises(TaskOptionsError):
            _make_task(LoadData, {"options": {}})

    def test_init_options__bulk_mode(self):
        t = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "file:///test.db",
                    "mapping": "mapping.yml",
                    "bulk_mode": "Serial",
                }
            },
        )

        assert t.bulk_mode == "Serial"

        t = _make_task(
            LoadData,
            {"options": {"database_url": "file:///test.db", "mapping": "mapping.yml"}},
        )

        assert t.bulk_mode is None

    def test_init_options__bulk_mode_wrong(self):
        with self.assertRaises(TaskOptionsError):
            _make_task(LoadData, {"options": {"bulk_mode": "Test"}})

    def test_init_options__database_url(self):
        t = _make_task(
            LoadData,
            {"options": {"database_url": "file:///test.db", "mapping": "mapping.yml"}},
        )

        assert t.options["database_url"] == "file:///test.db"
        assert t.options["sql_path"] is None

    def test_init_options__sql_path(self):
        t = _make_task(
            LoadData, {"options": {"sql_path": "test.sql", "mapping": "mapping.yml"}}
        )

        assert t.options["sql_path"] == "test.sql"
        assert t.options["database_url"] is None

    def test_expand_mapping_creates_after_steps(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "mapping_after.yml")
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        task._init_mapping()

        model = mock.Mock()
        model.__table__ = mock.Mock()
        model.__table__.primary_key.columns.keys.return_value = ["sf_id"]
        task.models = {"accounts": model, "contacts": model}

        task._expand_mapping()

        self.assertEqual({}, task.after_steps["Insert Opportunities"])
        self.assertEqual(
            [
                "Update Account Dependencies After Insert Contacts",
                "Update Contact Dependencies After Insert Contacts",
            ],
            list(task.after_steps["Insert Contacts"].keys()),
        )
        lookups = {}
        lookups["Id"] = MappingLookup(name="Id", table="accounts", key_field="sf_id")
        lookups["Primary_Contact__c"] = MappingLookup(
            table="contacts", name="Primary_Contact__c",
        )
        self.assertEqual(
            {
                "sf_object": "Account",
                "action": "update",
                "table": "accounts",
                "lookups": lookups,
                "fields": {},
            },
            task.after_steps["Insert Contacts"][
                "Update Account Dependencies After Insert Contacts"
            ],
        )
        lookups = {}
        lookups["Id"] = MappingLookup(name="Id", table="contacts", key_field="sf_id")
        lookups["ReportsToId"] = MappingLookup(table="contacts", name="ReportsToId")
        self.assertEqual(
            {
                "sf_object": "Contact",
                "action": "update",
                "table": "contacts",
                "fields": {},
                "lookups": lookups,
            },
            task.after_steps["Insert Contacts"][
                "Update Contact Dependencies After Insert Contacts"
            ],
        )
        self.assertEqual(
            ["Update Account Dependencies After Insert Accounts"],
            list(task.after_steps["Insert Accounts"].keys()),
        )
        lookups = {}
        lookups["Id"] = MappingLookup(name="Id", table="accounts", key_field="sf_id")
        lookups["ParentId"] = MappingLookup(table="accounts", name="ParentId")
        self.assertEqual(
            {
                "sf_object": "Account",
                "action": "update",
                "table": "accounts",
                "fields": {},
                "lookups": lookups,
            },
            task.after_steps["Insert Accounts"][
                "Update Account Dependencies After Insert Accounts"
            ],
        )

    def test_stream_queried_data__skips_empty_rows(self):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        task.sf = mock.Mock()

        mapping = {
            "sf_object": "Account",
            "action": "update",
            "fields": {},
            "lookups": {
                "Id": {"table": "accounts", "key_field": "account_id"},
                "ParentId": {"table": "accounts"},
            },
        }

        task._query_db = mock.Mock()
        task._query_db.return_value.yield_per = mock.Mock(
            return_value=[
                # Local Id, Loaded Id, Parent Id
                ["001000000001", "001000000005", "001000000007"],
                ["001000000002", "001000000006", "001000000008"],
                ["001000000003", "001000000009", None],
            ]
        )

        local_ids = []
        records = list(task._stream_queried_data(mapping, local_ids))
        self.assertEqual(
            [["001000000005", "001000000007"], ["001000000006", "001000000008"]],
            records,
        )

    def test_get_columns(self):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )

        fields = {}
        fields["Id"] = "sf_id"
        fields["Name"] = "Name"

        self.assertEqual(
            ["Name", "Industry", "RecordTypeId"],
            task._get_columns(
                {
                    "sf_object": "Account",
                    "action": "insert",
                    "fields": fields,
                    "static": {"Industry": "Technology"},
                    "record_type": "Organization",
                }
            ),
        )
        self.assertEqual(
            ["Id", "Name", "Industry", "RecordTypeId"],
            task._get_columns(
                {
                    "sf_object": "Account",
                    "action": "update",
                    "fields": fields,
                    "static": {"Industry": "Technology"},
                    "record_type": "Organization",
                }
            ),
        )

        fields["RecordTypeId"] = "recordtypeid"
        fields["AccountSite"] = "accountsite"

        self.assertEqual(
            ["Id", "Name", "AccountSite", "Industry", "RecordTypeId"],
            task._get_columns(
                {
                    "sf_object": "Account",
                    "action": "update",
                    "fields": fields,
                    "static": {"Industry": "Technology"},
                }
            ),
        )

    def test_get_statics(self):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        task.sf = mock.Mock()
        task.sf.query.return_value = {"records": [{"Id": "012000000000000"}]}

        self.assertEqual(
            ["Technology", "012000000000000"],
            task._get_statics(
                {
                    "sf_object": "Account",
                    "action": "insert",
                    "fields": {"Id": "sf_id", "Name": "Name"},
                    "static": {"Industry": "Technology"},
                    "record_type": "Organization",
                }
            ),
        )

    def test_get_statics_record_type_not_matched(self):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        task.sf = mock.Mock()
        task.sf.query.return_value = {"records": []}
        with self.assertRaises(BulkDataException) as e:
            task._get_statics(
                {
                    "sf_object": "Account",
                    "action": "insert",
                    "fields": {"Id": "sf_id", "Name": "Name"},
                    "static": {"Industry": "Technology"},
                    "record_type": "Organization",
                }
            ),
        assert "RecordType" in str(e.exception)

    @mock.patch("cumulusci.tasks.bulkdata.load.aliased")
    def test_query_db__joins_self_lookups(self, aliased):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        model = mock.Mock()
        task.models = {"accounts": model}
        task.metadata = mock.Mock()
        task.metadata.tables = {"accounts_sf_ids": mock.Mock()}
        task.session = mock.Mock()

        model.__table__ = mock.Mock()
        model.__table__.primary_key.columns.keys.return_value = ["sf_id"]
        columns = {"sf_id": mock.Mock(), "name": mock.Mock()}
        model.__table__.columns = columns

        mapping = {
            "sf_object": "Account",
            "table": "accounts",
            "action": "update",
            "oid_as_pk": True,
            "fields": {"Id": "sf_id", "Name": "name"},
            "lookups": {
                "ParentId": MappingLookup(
                    table="accounts", key_field="parent_id", name="ParentId"
                )
            },
        }

        task._query_db(mapping)

        # Validate that the column set is accurate
        task.session.query.assert_called_once_with(
            model.sf_id,
            model.__table__.columns["name"],
            aliased.return_value.columns.sf_id,
        )

        # Validate that we asked for an outer join on the self-lookup
        aliased.assert_called_once_with(task.metadata.tables["accounts_sf_ids"])
        task.session.query.return_value.outerjoin.assert_called_once_with(
            aliased.return_value, False
        )

    def test_convert(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )
        self.assertIsInstance(task._convert(datetime.now()), str)

    def test_initialize_id_table__already_exists(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )
        task.mapping = {}
        task._init_db()
        id_table = Table(
            "test_sf_ids", task.metadata, Column("id", Unicode(255), primary_key=True)
        )
        id_table.create()
        task._initialize_id_table({"table": "test"}, True)
        new_id_table = task.metadata.tables["test_sf_ids"]
        self.assertFalse(new_id_table is id_table)

    def test_initialize_id_table__already_exists_and_should_not_reset_table(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )
        task.mapping = {}
        task._init_db()
        id_table = Table(
            "test_sf_ids", task.metadata, Column("id", Unicode(255), primary_key=True)
        )
        id_table.create()
        table_name = task._initialize_id_table({"table": "test"}, False)
        assert table_name == "test_sf_ids"
        new_id_table = task.metadata.tables["test_sf_ids"]
        assert new_id_table is id_table

    def test_run_task__exception_failure(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )
        task._init_db = mock.Mock()
        task._init_mapping = mock.Mock()
        task._execute_step = mock.Mock(
            return_value=DataOperationJobResult(
                DataOperationStatus.JOB_FAILURE, [], 0, 0
            )
        )
        task.mapping = {"Test": {"test": "test"}}

        with self.assertRaises(BulkDataException):
            task()

    def test_process_job_results__insert_success(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task._initialize_id_table = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()

        local_ids = ["1"]

        step = MockBulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult("001111111111111", True, None)]

        mapping = {"table": "Account", "action": "insert"}
        task._process_job_results(mapping, step, local_ids)

        task.session.connection.assert_called_once()
        task._initialize_id_table.assert_called_once_with(mapping, True)
        task._sql_bulk_insert_from_records.assert_called_once()
        task.session.commit.assert_called_once()

    def test_process_job_results__insert_rows_fail(self):
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite://",
                    "mapping": "mapping.yml",
                    "ignore_row_errors": True,
                }
            },
        )

        task.session = mock.Mock()
        task._initialize_id_table = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task.logger = mock.Mock()

        local_ids = ["1", "2", "3", "4"]

        step = MockBulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step.job_result = DataOperationJobResult(
            DataOperationStatus.ROW_FAILURE, [], 4, 4
        )
        step.end = mock.Mock()
        step.results = [
            DataOperationResult("001111111111111", False, None),
            DataOperationResult("001111111111112", False, None),
            DataOperationResult("001111111111113", False, None),
            DataOperationResult("001111111111114", False, None),
        ]

        mapping = {"table": "Account", "action": "insert"}
        task._process_job_results(mapping, step, local_ids)

        task.session.connection.assert_called_once()
        task._initialize_id_table.assert_called_once_with(mapping, True)
        task._sql_bulk_insert_from_records.assert_not_called()
        task.session.commit.assert_called_once()
        assert len(task.logger.mock_calls) == 4

    def test_process_job_results__update_success(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task._initialize_id_table = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()

        local_ids = ["1"]

        step = MockBulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult("001111111111111", True, None)]

        mapping = {"table": "Account", "action": "update"}
        task._process_job_results(mapping, step, local_ids)

        task.session.connection.assert_not_called()
        task._initialize_id_table.assert_not_called()
        task._sql_bulk_insert_from_records.assert_not_called()
        task.session.commit.assert_not_called()

    def test_process_job_results__exception_failure(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task._initialize_id_table = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()

        local_ids = ["1"]

        step = MockBulkApiDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPDATE,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult(None, False, "message")]
        step.end()

        mapping = {"table": "Account", "action": "update"}

        with self.assertRaises(BulkDataException) as ex:
            task._process_job_results(mapping, step, local_ids)

        self.assertIn("Error on record with id", str(ex.exception))
        self.assertIn("message", str(ex.exception))

    def test_generate_results_id_map__success(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        step = mock.Mock()
        step.get_results.return_value = iter(
            [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("001000000000001", True, None),
                DataOperationResult("001000000000002", True, None),
            ]
        )

        generator = task._generate_results_id_map(
            step, ["001000000000009", "001000000000010", "001000000000011"]
        )

        assert list(generator) == [
            ("001000000000009", "001000000000000"),
            ("001000000000010", "001000000000001"),
            ("001000000000011", "001000000000002"),
        ]

    def test_generate_results_id_map__exception_failure(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        step = mock.Mock()
        step.get_results.return_value = iter(
            [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult(None, False, "error"),
                DataOperationResult("001000000000002", True, None),
            ]
        )

        with self.assertRaises(BulkDataException) as ex:
            list(
                task._generate_results_id_map(
                    step, ["001000000000009", "001000000000010", "001000000000011"]
                )
            )

        self.assertIn("Error on record", str(ex.exception))
        self.assertIn("001000000000010", str(ex.exception))

    def test_generate_results_id_map__respects_silent_error_flag(self):
        task = _make_task(
            LoadData,
            {
                "options": {
                    "ignore_row_errors": True,
                    "database_url": "sqlite://",
                    "mapping": "mapping.yml",
                }
            },
        )

        step = mock.Mock()
        step.get_results.return_value = iter(
            [DataOperationResult(None, False, None)] * 15
        )

        with mock.patch.object(task.logger, "warning") as warning:
            generator = task._generate_results_id_map(
                step, ["001000000000009", "001000000000010", "001000000000011"] * 15
            )
            _ = list(generator)  # generate the errors

        assert len(warning.mock_calls) == task.row_warning_limit + 1 == 11
        assert "warnings suppressed" in str(warning.mock_calls[-1])

        step = mock.Mock()
        step.get_results.return_value = iter(
            [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult(None, False, None),
                DataOperationResult("001000000000002", True, None),
            ]
        )

        generator = task._generate_results_id_map(
            step, ["001000000000009", "001000000000010", "001000000000011"]
        )

        assert list(generator) == [
            ("001000000000009", "001000000000000"),
            ("001000000000011", "001000000000002"),
        ]

    @mock.patch("cumulusci.tasks.bulkdata.load.BulkApiDmlOperation")
    def test_execute_step__record_type_mapping(self, step_mock):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task._load_record_types = mock.Mock()
        task._process_job_results = mock.Mock()

        task._execute_step(
            MappingStep(
                **{
                    "sf_object": "Account",
                    "action": "insert",
                    "fields": {"Name": "Name"},
                }
            )
        )

        task._load_record_types.assert_not_called()

        task._execute_step(
            MappingStep(
                **{
                    "sf_object": "Account",
                    "action": "insert",
                    "fields": {"Name": "Name", "RecordTypeId": "RecordTypeId"},
                }
            )
        )
        task._load_record_types.assert_called_once_with(
            ["Account"], task.session.connection.return_value
        )

    def test_query_db__record_type_mapping(self):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        model = mock.Mock()
        task.models = {"accounts": model}
        task.metadata = mock.Mock()
        task.metadata.tables = {
            "Account_rt_target_mapping": mock.Mock(),
            "Account_rt_mapping": mock.Mock(),
        }
        task.session = mock.Mock()

        model.__table__ = mock.Mock()
        model.__table__.primary_key.columns.keys.return_value = ["sf_id"]
        columns = {"sf_id": mock.Mock(), "name": mock.Mock()}
        model.__table__.columns = columns

        mapping = OrderedDict(
            sf_object="Account",
            table="accounts",
            action="insert",
            oid_as_pk=True,
            fields=OrderedDict(Id="sf_id", Name="name", RecordTypeId="RecordTypeId"),
        )

        task._query_db(mapping)

        # Validate that the column set is accurate
        task.session.query.assert_called_once_with(
            model.sf_id,
            model.__table__.columns["name"],
            task.metadata.tables["Account_rt_target_mapping"].columns.record_type_id,
        )

        # Validate that we asked for the right joins on the record type tables
        task.session.query.return_value.outerjoin.assert_called_once_with(
            task.metadata.tables["Account_rt_mapping"], False
        )
        task.session.query.return_value.outerjoin.return_value.outerjoin.assert_called_once_with(
            task.metadata.tables["Account_rt_target_mapping"], False
        )

    @mock.patch("cumulusci.tasks.bulkdata.load.automap_base")
    def test_init_db__record_type_mapping(self, base):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        def create_table_mock(table_name):
            task.models[table_name] = mock.Mock()

        task._create_record_type_table = mock.Mock(side_effect=create_table_mock)
        task.models = mock.Mock()
        task.metadata = mock.Mock()

        task._init_mapping()
        task.mapping["Insert Households"]["fields"]["RecordTypeId"] = "RecordTypeId"
        task._init_db()
        task._create_record_type_table.assert_called_once_with(
            "Account_rt_target_mapping"
        )

    def test_load_record_types(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        conn = mock.Mock()
        task._extract_record_types = mock.Mock()
        task._load_record_types(["Account", "Contact"], conn)
        task._extract_record_types.assert_has_calls(
            [
                unittest.mock.call("Account", "Account_rt_target_mapping", conn),
                unittest.mock.call("Contact", "Contact_rt_target_mapping", conn),
            ]
        )

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.load.BulkApiDmlOperation")
    def test_run__autopk(self, step_mock):
        responses.add(
            method="GET",
            url="https://example.com/services/data/v46.0/query/?q=SELECT+Id+FROM+RecordType+WHERE+SObjectType%3D%27Account%27AND+DeveloperName+%3D+%27HH_Account%27+LIMIT+1",
            body=json.dumps({"records": [{"Id": "1"}]}),
            status=200,
        )

        mapping_file = "mapping_v2.yml"
        base_path = os.path.dirname(__file__)
        db_path = os.path.join(base_path, "testdata.db")
        mapping_path = os.path.join(base_path, mapping_file)
        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "testdata.db")
            shutil.copyfile(db_path, tmp_db_path)

            task = _make_task(
                LoadData,
                {
                    "options": {
                        "database_url": f"sqlite:///{tmp_db_path}",
                        "mapping": mapping_path,
                    }
                },
            )
            task.bulk = mock.Mock()
            task.sf = mock.Mock()
            step = MockBulkApiDmlOperation(
                sobject="Contact",
                operation=DataOperationType.INSERT,
                api_options={},
                context=task,
                fields=[],
            )
            step_mock.return_value = step

            step.results = [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("003000000000000", True, None),
                DataOperationResult("003000000000001", True, None),
            ]

            task()

            assert step.records == [
                ["TestHousehold", "1"],
                ["Test", "User", "test@example.com", "001000000000000"],
                ["Error", "User", "error@example.com", "001000000000000"],
            ]

            hh_ids = task.session.query(
                *task.metadata.tables["households_sf_ids"].columns
            ).one()
            assert hh_ids == ("1", "001000000000000")

            task.session.close()

    def test_run__complex_lookups(self):
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        task._init_mapping()
        assert (
            task.mapping["Insert Accounts"]["lookups"]["ParentId"]["after"]
            == "Insert Accounts"
        )
        task.models = {}
        task.models["accounts"] = mock.MagicMock()
        task.models["accounts"].__table__ = mock.MagicMock()
        task.models["accounts"].__table__.primary_key.columns = mock.MagicMock()
        task.models["accounts"].__table__.primary_key.columns.keys = mock.Mock(
            return_value=["Id"]
        )
        task._expand_mapping()
        assert (
            task.mapping["Insert Accounts"]["lookups"]["ParentId"]["after"]
            == "Insert Accounts"
        )

    def test_load__inferred_keyfield_camelcase(self):
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._init_mapping()

        class FakeModel:
            ParentId = mock.MagicMock()

        assert (
            task.mapping["Insert Accounts"]["lookups"]["ParentId"].get_lookup_key_field(
                FakeModel()
            )
            == "ParentId"
        )

    def test_load__inferred_keyfield_snakecase(self):
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._init_mapping()

        class FakeModel:
            parent_id = mock.MagicMock()

        assert (
            task.mapping["Insert Accounts"]["lookups"]["ParentId"].get_lookup_key_field(
                FakeModel()
            )
            == "parent_id"
        )
