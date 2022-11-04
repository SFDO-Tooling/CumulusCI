import io
import json
import logging
import os
import random
import shutil
import string
import tempfile
from contextlib import nullcontext
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import pytest
import responses
from sqlalchemy import Column, Table, Unicode, create_engine

from cumulusci.core.exceptions import BulkDataException, TaskOptionsError
from cumulusci.salesforce_api.org_schema import get_org_schema
from cumulusci.tasks.bulkdata import LoadData
from cumulusci.tasks.bulkdata.mapping_parser import MappingLookup, MappingStep
from cumulusci.tasks.bulkdata.step import (
    BulkApiDmlOperation,
    DataApi,
    DataOperationJobResult,
    DataOperationResult,
    DataOperationStatus,
    DataOperationType,
)
from cumulusci.tasks.bulkdata.tests.utils import (
    FakeBulkAPI,
    FakeBulkAPIDmlOperation,
    _make_task,
)
from cumulusci.tests.util import (
    CURRENT_SF_API_VERSION,
    DummyOrgConfig,
    assert_max_memory_usage,
    mock_describe_calls,
)
from cumulusci.utils import temporary_dir


class FakePath:
    def __init__(self, real_path, does_exist):
        self.does_exist = does_exist
        self.real_path = real_path

    def exists(self):
        return self.does_exist

    def __str__(self):
        return self.real_path


class FakePathFileSystem:
    def __init__(self, existing_paths):
        self.paths = [Path(path) for path in existing_paths]

    def __call__(self, *filename):
        filename_parts = [str(el) for el in filename]
        real_filename = str(Path(*filename_parts))
        return FakePath(real_filename, (Path(real_filename) in self.paths))


class TestLoadData:
    mapping_file = "mapping_v1.yml"

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.load.get_dml_operation")
    def test_run(self, dml_mock):
        responses.add(
            method="GET",
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id+FROM+RecordType+WHERE+SObjectType%3D%27Account%27AND+DeveloperName+%3D+%27HH_Account%27+LIMIT+1",
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
                        "set_recently_viewed": False,
                    }
                },
            )

            task.bulk = mock.Mock()
            task.sf = mock.Mock()

            step = FakeBulkAPIDmlOperation(
                sobject="Contact",
                operation=DataOperationType.INSERT,
                api_options={},
                context=task,
                fields=[],
            )
            dml_mock.return_value = step

            step.results = [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("003000000000000", True, None),
                DataOperationResult("003000000000001", True, None),
            ]

            mock_describe_calls()
            task()

            assert step.records == [
                ["TestHousehold", "1"],
                ["Test", "User", "test@example.com", "001000000000000"],
                ["Error", "User", "error@example.com", "001000000000000"],
            ]
            with create_engine(task.options["database_url"]).connect() as c:
                hh_ids = next(c.execute("SELECT * from households_sf_ids"))
                assert hh_ids == ("1", "001000000000000")

    def test_run_task__start_step(self):
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite://",
                    "mapping": "mapping.yml",
                    "start_step": "Insert Contacts",
                    "set_recently_viewed": False,
                }
            },
        )
        task._init_db = mock.Mock(return_value=nullcontext())
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
            {
                "options": {
                    "database_url": "sqlite://",
                    "mapping": "mapping.yml",
                    "set_recently_viewed": False,
                }
            },
        )
        task._init_db = mock.Mock(return_value=nullcontext())
        task._init_mapping = mock.Mock()
        task._expand_mapping = mock.Mock()
        task.mapping = {}
        one = task.mapping["Insert Households"] = mock.Mock()
        two = task.mapping["Insert Contacts"] = mock.Mock()
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
            [mock.call(one), mock.call(4), mock.call(5), mock.call(two), mock.call(3)]
        )

    def test_run_task__after_steps_failure(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )
        task._init_db = mock.Mock(return_value=nullcontext())
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
        with pytest.raises(BulkDataException):
            task()

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.load.get_dml_operation")
    def test_run__sql(self, dml_mock):
        responses.add(
            method="GET",
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id+FROM+RecordType+WHERE+SObjectType%3D%27Account%27AND+DeveloperName+%3D+%27HH_Account%27+LIMIT+1",
            body=json.dumps({"records": [{"Id": "1"}]}),
            status=200,
        )

        base_path = os.path.dirname(__file__)
        sql_path = os.path.join(base_path, "testdata.sql")
        mapping_path = os.path.join(base_path, self.mapping_file)

        task = _make_task(
            LoadData,
            {
                "options": {
                    "sql_path": sql_path,
                    "mapping": mapping_path,
                    "set_recently_viewed": False,
                }
            },
        )
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        step = FakeBulkAPIDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        dml_mock.return_value = step
        step.results = [
            DataOperationResult("001000000000000", True, None),
            DataOperationResult("003000000000000", True, None),
            DataOperationResult("003000000000001", True, None),
        ]
        mock_describe_calls()
        task()

        assert step.records == [
            ["TestHousehold", "1"],
            ["Test☃", "User", "test@example.com", "001000000000000"],
            ["Error", "User", "error@example.com", "001000000000000"],
        ]

    def test_init_options__missing_input(self):
        t = _make_task(LoadData, {"options": {}})

        assert t.options["sql_path"] == "datasets/sample.sql"
        assert t.options["mapping"] == "datasets/mapping.yml"

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
        with pytest.raises(TaskOptionsError):
            _make_task(LoadData, {"options": {"bulk_mode": "Test"}})

    def test_init_options__database_url(self):
        t = _make_task(
            LoadData,
            {"options": {"database_url": "file:///test.db", "mapping": "mapping.yml"}},
        )

        assert t.options["database_url"] == "file:///test.db"
        assert t.options["sql_path"] is None
        assert t.has_dataset is True

    def test_init_options__sql_path_and_mapping(self):
        t = _make_task(
            LoadData,
            {
                "options": {
                    "sql_path": "datasets/test.sql",
                    "mapping": "datasets/test.yml",
                }
            },
        )

        assert t.options["sql_path"] == "datasets/test.sql"
        assert t.options["mapping"] == "datasets/test.yml"
        assert t.options["database_url"] is None
        assert t.has_dataset is True

    def test_init_options__org_shape_match_only__true(self):
        dataset_path = "datasets/dev/dev.dataset.sql"
        mapping_path = "datasets/dev/dev.mapping.yml"
        fake_paths = FakePathFileSystem([mapping_path, dataset_path, "datasets/dev"])
        with mock.patch("cumulusci.tasks.bulkdata.load.Path", fake_paths):
            org_config = DummyOrgConfig(
                {
                    "config_name": "dev",
                },
                "test",
            )
            t = _make_task(
                LoadData,
                {
                    "options": {
                        "sql_path": "datasets/test.sql",
                        "mapping": "datasets/mapping.yml",
                        "org_shape_match_only": True,
                    }
                },
                org_config,
            )

            assert t.options["sql_path"] == dataset_path
            assert t.options["mapping"] == mapping_path
            assert t.options["database_url"] is None
            assert t.has_dataset is True

    def test_init_options__org_shape_match_only__false(self):
        """Matching paths exist but we do not use them."""
        dataset_path = "datasets/dev/dev.dataset.sql"
        mapping_path = "datasets/dev/dev.mapping.yml"
        fake_paths = FakePathFileSystem([mapping_path, dataset_path, "datasets/dev"])
        with mock.patch("cumulusci.tasks.bulkdata.load.Path", fake_paths):
            org_config = DummyOrgConfig(
                {
                    "config_name": "dev",
                },
                "test",
            )
            t = _make_task(
                LoadData,
                {
                    "options": {
                        "sql_path": "datasets/test.sql",
                        "mapping": "datasets/mapping.yml",
                        #  "org_shape_match_only": False, DEFAULTED
                    }
                },
                org_config,
            )

            assert t.options["sql_path"] == "datasets/test.sql"
            assert t.options["mapping"] == "datasets/mapping.yml"
            assert t.options["database_url"] is None
            assert t.has_dataset is True

    def test_init_options__sql_path_no_mapping(self):
        t = _make_task(LoadData, {"options": {"sql_path": "datasets/test.sql"}})

        assert t.options["sql_path"] == "datasets/test.sql"
        assert t.options["mapping"] == "datasets/mapping.yml"
        assert t.options["database_url"] is None
        assert t.has_dataset is True

    def test_init_options__mapping_no_sql_path(self):
        t = _make_task(LoadData, {"options": {"mapping": "datasets/test.yml"}})

        assert t.options["sql_path"] == "datasets/sample.sql"
        assert t.options["mapping"] == "datasets/test.yml"
        assert t.options["database_url"] is None
        assert t.has_dataset is True

    def test_init_datasets__matching_dataset(self):
        dataset_path = "datasets/dev/dev.dataset.sql"
        mapping_path = "datasets/dev/dev.mapping.yml"
        fake_paths = FakePathFileSystem([mapping_path, dataset_path, "datasets/dev"])
        with mock.patch("cumulusci.tasks.bulkdata.load.Path", fake_paths):
            org_config = DummyOrgConfig(
                {
                    "config_name": "dev",
                },
                "test",
            )
            t = _make_task(LoadData, {}, org_config=org_config)
            assert t.options["sql_path"] == dataset_path
            assert t.options["mapping"] == mapping_path
            assert t.has_dataset is True

    def test_init_datasets__matching_dataset_dir__missing_dataset_path(self, caplog):
        caplog.set_level(logging.WARNING)
        mapping_path = "datasets/dev/dev.mapping.yml"
        fake_paths = FakePathFileSystem([mapping_path, "datasets/dev"])
        org_shape = "dev"
        with mock.patch("cumulusci.tasks.bulkdata.load.Path", fake_paths):
            org_config = DummyOrgConfig(
                {
                    "config_name": org_shape,
                },
                "test",
            )
            t = _make_task(LoadData, {}, org_config=org_config)
            assert t.options.get("sql_path") is None
            assert t.options.get("mapping") is None
            assert (
                f"Found datasets/{org_shape} but it did not contain {org_shape}.mapping.yml and {org_shape}.dataset.yml."
                in caplog.text
            )
            assert t.has_dataset is False

    def test_init_datasets__matching_dataset_dir__missing_mapping_path(self, caplog):
        caplog.set_level(logging.WARNING)
        dataset_path = "datasets/dev/dev.dataset.sql"
        fake_paths = FakePathFileSystem([dataset_path, "datasets/dev"])
        org_shape = "dev"
        with mock.patch("cumulusci.tasks.bulkdata.load.Path", fake_paths):
            org_config = DummyOrgConfig(
                {
                    "config_name": org_shape,
                },
                "test",
            )
            t = _make_task(LoadData, {}, org_config=org_config)
            assert t.options.get("sql_path") is None
            assert t.options.get("mapping") is None
            assert (
                f"Found datasets/{org_shape} but it did not contain {org_shape}.mapping.yml and {org_shape}.dataset.yml."
                in caplog.text
            )
            assert t.has_dataset is False

    def test_init_datasets__no_matching_dataset__use_default(self):
        dataset_path = "datasets/sample.sql"
        mapping_path = "datasets/mapping.yml"
        fake_paths = FakePathFileSystem([dataset_path, mapping_path])
        with mock.patch("cumulusci.tasks.bulkdata.load.Path", fake_paths):
            org_config = DummyOrgConfig(
                {
                    "config_name": "dev",
                },
                "test",
            )
            t = _make_task(LoadData, {}, org_config=org_config)
            assert t.options["sql_path"] == "datasets/sample.sql"
            assert t.options["mapping"] == "datasets/mapping.yml"
            assert t.has_dataset is True

    def test_init_datasets__no_matching_dataset__skip_default(self):
        dataset_path = "datasets/sample.sql"
        mapping_path = "datasets/mapping.yml"
        fake_paths = FakePathFileSystem([dataset_path, mapping_path])
        with mock.patch("cumulusci.tasks.bulkdata.load.Path", fake_paths):
            org_config = DummyOrgConfig(
                {
                    "config_name": "dev",
                },
                "test",
            )
            t = _make_task(
                LoadData,
                {
                    "options": {
                        "org_shape_match_only": True,
                    }
                },
                org_config=org_config,
            )
            assert t.options["sql_path"] is None
            assert t.options["mapping"] is None
            assert t.has_dataset is False

    def test_init_datasets__no_matching_dataset_no_load_scratch(self, caplog):
        caplog.set_level(logging.INFO)
        fake_paths = FakePathFileSystem([])
        with mock.patch("cumulusci.tasks.bulkdata.load.Path", fake_paths):
            org_config = DummyOrgConfig(
                {
                    "config_name": "dev",
                },
                "test",
            )
            t = _make_task(LoadData, {}, org_config=org_config)
            assert t.has_dataset is False
            assert t.options.get("sql_path") is None
            assert t.options.get("mapping") is None
            t._run_task()
            assert (
                "No data will be loaded because there was no dataset found matching your org shape name ('dev')."
                in caplog.text
            )

    def test_init_datasets__no_matching_dataset_no_load_persistent(self, caplog):
        caplog.set_level(logging.INFO)
        fake_paths = FakePathFileSystem([])
        with mock.patch("cumulusci.tasks.bulkdata.load.Path", fake_paths):
            org_config = DummyOrgConfig(
                {
                    "config_name": None,
                },
                "test",
            )
            t = _make_task(LoadData, {}, org_config=org_config)
            assert t.has_dataset is False
            assert t.options.get("sql_path") is None
            assert t.options.get("mapping") is None
            t._run_task()
            assert (
                "No data will be loaded because this is a persistent org and no dataset was specified."
                in caplog.text
            )

    @mock.patch("cumulusci.tasks.bulkdata.load.validate_and_inject_mapping")
    def test_init_mapping_passes_options_to_validate(self, validate_and_inject_mapping):
        base_path = os.path.dirname(__file__)

        t = _make_task(
            LoadData,
            {
                "options": {
                    "sql_path": "test.sql",
                    "mapping": os.path.join(base_path, self.mapping_file),
                    "inject_namespaces": True,
                    "drop_missing_schema": True,
                }
            },
        )

        t._init_task()
        t._init_mapping()

        validate_and_inject_mapping.assert_called_once_with(
            mapping=t.mapping,
            sf=t.sf,
            namespace=t.project_config.project__package__namespace,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=True,
            drop_missing=True,
        )

    @responses.activate
    def test_expand_mapping_creates_after_steps(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "mapping_after.yml")
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        mock_describe_calls()
        task._init_task()
        task._init_mapping()

        model = mock.Mock()
        model.__table__ = mock.Mock()
        model.__table__.primary_key.columns.keys.return_value = ["sf_id"]
        task.models = {"accounts": model, "contacts": model}

        task._expand_mapping()

        assert {} == task.after_steps["Insert Opportunities"]
        assert [
            "Update Account Dependencies After Insert Contacts",
            "Update Contact Dependencies After Insert Contacts",
        ] == list(task.after_steps["Insert Contacts"].keys())
        lookups = {}
        lookups["Id"] = MappingLookup(name="Id", table="accounts", key_field="sf_id")
        lookups["Primary_Contact__c"] = MappingLookup(
            table="contacts", name="Primary_Contact__c"
        )
        assert (
            MappingStep(
                sf_object="Account",
                api=DataApi.BULK,
                action=DataOperationType.UPDATE,
                table="accounts",
                lookups=lookups,
                fields={},
            )
            == task.after_steps["Insert Contacts"][
                "Update Account Dependencies After Insert Contacts"
            ]
        )
        lookups = {}
        lookups["Id"] = MappingLookup(name="Id", table="contacts", key_field="sf_id")
        lookups["ReportsToId"] = MappingLookup(table="contacts", name="ReportsToId")
        assert (
            MappingStep(
                sf_object="Contact",
                api=DataApi.BULK,
                action=DataOperationType.UPDATE,
                table="contacts",
                fields={},
                lookups=lookups,
            )
            == task.after_steps["Insert Contacts"][
                "Update Contact Dependencies After Insert Contacts"
            ]
        )
        assert ["Update Account Dependencies After Insert Accounts"] == list(
            task.after_steps["Insert Accounts"].keys()
        )
        lookups = {}
        lookups["Id"] = MappingLookup(name="Id", table="accounts", key_field="sf_id")
        lookups["ParentId"] = MappingLookup(table="accounts", name="ParentId")
        assert (
            MappingStep(
                sf_object="Account",
                api=DataApi.BULK,
                action=DataOperationType.UPDATE,
                table="accounts",
                fields={},
                lookups=lookups,
            )
            == task.after_steps["Insert Accounts"][
                "Update Account Dependencies After Insert Accounts"
            ]
        )

    def test_stream_queried_data__skips_empty_rows(self):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        task.sf = mock.Mock()

        mapping = MappingStep(
            **{
                "sf_object": "Account",
                "action": "update",
                "fields": {},
                "lookups": {
                    "Id": MappingLookup(
                        **{"table": "accounts", "key_field": "account_id"}
                    ),
                    "ParentId": MappingLookup(**{"table": "accounts"}),
                },
            }
        )

        task._query_db = mock.Mock()
        task._query_db.return_value.yield_per = mock.Mock(
            return_value=[
                # Local Id, Loaded Id, Parent Id
                ["001000000001", "001000000005", "001000000007"],
                ["001000000002", "001000000006", "001000000008"],
                ["001000000003", "001000000009", None],
            ]
        )

        with tempfile.TemporaryFile("w+t") as local_ids:
            records = list(
                task._stream_queried_data(mapping, local_ids, task._query_db(mapping))
            )
            assert [
                ["001000000005", "001000000007"],
                ["001000000006", "001000000008"],
            ] == records

    @responses.activate
    def test_stream_queried_data__adjusts_relative_dates(self):
        mock_describe_calls()
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        task._init_task()
        mapping = MappingStep(
            sf_object="Contact",
            action="insert",
            fields=["Birthdate"],
            anchor_date="2020-07-01",
        )

        task._query_db = mock.Mock()
        task._query_db.return_value.yield_per = mock.Mock(
            return_value=[
                # Local Id, Loaded Id, EmailBouncedDate
                ["001000000001", "2020-07-10"],
                ["001000000003", None],
            ]
        )

        local_ids = io.StringIO()
        records = list(
            task._stream_queried_data(mapping, local_ids, task._query_db(mapping))
        )
        assert [[(date.today() + timedelta(days=9)).isoformat()], [None]] == records

    def test_get_statics(self):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        task.sf = mock.Mock()
        task.sf.query.return_value = {"records": [{"Id": "012000000000000"}]}

        assert ["Technology", "012000000000000"] == task._get_statics(
            MappingStep(
                sf_object="Account",
                fields={"Id": "sf_id", "Name": "Name"},
                static={"Industry": "Technology"},
                record_type="Organization",
            )
        )

    def test_get_statics_record_type_not_matched(self):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        task.sf = mock.Mock()
        task.sf.query.return_value = {"records": []}
        with pytest.raises(BulkDataException) as e:
            task._get_statics(
                MappingStep(
                    sf_object="Account",
                    action="insert",
                    fields={"Id": "sf_id", "Name": "Name"},
                    static={"Industry": "Technology"},
                    record_type="Organization",
                )
            ),
        assert "RecordType" in str(e.value)

    def test_query_db__joins_self_lookups(self):
        _validate_query_for_mapping_step(
            sql_path=Path(__file__).parent / "test_query_db__joins_self_lookups.sql",
            mapping=Path(__file__).parent / "test_query_db__joins_self_lookups.yml",
            mapping_step_name="Update Accounts",
            expected="""SELECT accounts.sf_id AS accounts_sf_id, accounts."Name" AS "accounts_Name", accounts_sf_ids_1.sf_id AS accounts_sf_ids_1_sf_id
FROM accounts LEFT OUTER JOIN accounts_sf_ids AS accounts_sf_ids_1 ON accounts_sf_ids_1.id = accounts.parent_id ORDER BY accounts.parent_id
        """,
        )

    @responses.activate
    def test_query_db__person_accounts_enabled__account_mapping(self):
        responses.add(
            method="GET",
            url="https://example.com/services/data",
            json=[{"version": CURRENT_SF_API_VERSION}],
            status=200,
        )
        responses.add(
            method="GET",
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/sobjects/Account/describe",
            json={"fields": [{"name": "Id"}, {"name": "IsPersonAccount"}]},
        )

        _validate_query_for_mapping_step(
            sql_path=Path(__file__).parent / "person_accounts.sql",
            mapping=Path(__file__).parent / "update_person_accounts.yml",
            mapping_step_name="Update Account",
            expected="""SELECT
                "Account".id AS "Account_id",
                "Account"."FirstName" AS "Account_FirstName",
                "Account"."LastName" AS "Account_LastName",
                "Account"."PersonMailingStreet" AS "Account_PersonMailingStreet",
                "Account"."PersonMailingCity" AS "Account_PersonMailingCity",
                "Account"."PersonMailingState" AS "Account_PersonMailingState",
                "Account"."PersonMailingCountry" AS "Account_PersonMailingCountry",
                "Account"."PersonMailingPostalCode" AS "Account_PersonMailingPostalCode",
                "Account"."PersonEmail" AS "Account_PersonEmail",
                "Account"."Phone" AS "Account_Phone",
                "Account"."PersonMobilePhone" AS "Account_PersonMobilePhone"
                FROM "Account"
        """,
        )

    @responses.activate
    def test_query_db__person_accounts_disabled__account_mapping(self):
        responses.add(
            method="GET",
            url="https://example.com/services/data",
            json=[{"version": CURRENT_SF_API_VERSION}],
            status=200,
        )
        responses.add(
            method="GET",
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/sobjects/Account/describe",
            json={"fields": [{"name": "Id"}]},
        )
        with pytest.raises(BulkDataException) as e:
            _validate_query_for_mapping_step(
                sql_path=Path(__file__).parent / "person_accounts.sql",
                mapping=Path(__file__).parent / "update_person_accounts.yml",
                mapping_step_name="Update Account",
                expected="",
            )

        assert "Person Account" in str(e.value)

    # This test should be rewritten into a light-mocking style but creating the
    # sample data is non-trivial work that might require some collaboration
    @mock.patch("cumulusci.tasks.bulkdata.query_transformers.aliased")
    def test_query_db__person_accounts_enabled__contact_mapping(self, aliased):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        model = mock.Mock()
        task.models = {"contacts": model}
        task.metadata = mock.Mock()
        task.metadata.tables = {
            "contacts_sf_ids": mock.Mock(),
            "accounts_sf_ids": mock.Mock(),
        }
        task.session = mock.Mock()
        task._can_load_person_accounts = mock.Mock(return_value=True)
        # task._filter_out_person_account_records = mock.Mock() # TODO: Replace this with a better test

        # Make mock query chainable
        task.session.query.return_value = task.session.query
        task.session.query.filter.return_value = task.session.query
        task.session.query.outerjoin.return_value = task.session.query
        task.session.query.order_by.return_value = task.session.query
        task.session.query.add_columns.return_value = task.session.query

        model.__table__ = mock.Mock()
        model.__table__.primary_key.columns.keys.return_value = ["sf_id"]
        columns = {
            "sf_id": mock.Mock(),
            "name": mock.Mock(),
            "IsPersonAccount": mock.Mock(),
        }
        model.__table__.columns = columns

        mapping = MappingStep(
            sf_object="Contact",
            table="contacts",
            action=DataOperationType.UPDATE,
            fields={"Id": "sf_id", "Name": "name"},
            lookups={
                "ParentId": MappingLookup(
                    table="accounts", key_field="parent_id", name="ParentId"
                )
            },
        )

        query = task._query_db(mapping)
        assert (
            task.session.query == query
        )  # check that query chaining from above worked.

        query_columns, added_filters = _inspect_query(query)
        # Validate that the column set is accurate
        assert query_columns == (
            model.sf_id,
            model.__table__.columns["name"],
            aliased.return_value.columns.sf_id,
        )

        # Validate person contact records WERE filtered out
        filter_out_contacts, *rest = added_filters
        assert not rest
        assert filter_out_contacts.right.value == "false"
        assert (
            added_filters[0].left.clause_expr.element.clauses[0].value
            == columns["IsPersonAccount"]
        )

    # This test should be rewritten into a light-mocking style but creating the
    # sample data is non-trivial work that might require some collaboration
    @mock.patch("cumulusci.tasks.bulkdata.query_transformers.aliased")
    def test_query_db__person_accounts_disabled__contact_mapping(self, aliased):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        model = mock.Mock()
        task.models = {"contacts": model}
        task.metadata = mock.Mock()
        task.metadata.tables = {
            "contacts_sf_ids": mock.Mock(),
            "accounts_sf_ids": mock.Mock(),
        }
        task.session = mock.Mock()
        task._can_load_person_accounts = mock.Mock(return_value=False)
        # task._filter_out_person_account_records = mock.Mock() # TODO: Replace this with a better test

        # Make mock query chainable
        task.session.query.return_value = task.session.query
        task.session.query.filter.return_value = task.session.query
        task.session.query.outerjoin.return_value = task.session.query
        task.session.query.order_by.return_value = task.session.query
        task.session.query.add_columns.return_value = task.session.query

        model.__table__ = mock.Mock()
        model.__table__.primary_key.columns.keys.return_value = ["sf_id"]
        columns = {
            "sf_id": mock.Mock(name="contacts.sf_id"),
            "name": mock.Mock(name="contacts.name"),
            "IsPersonAccount": mock.Mock(name="contacts.IsPersonAccount"),
        }
        model.__table__.columns = columns

        mapping = MappingStep(
            sf_object="Contact",
            table="contacts",
            action=DataOperationType.UPDATE,
            fields={"Id": "sf_id", "Name": "name"},
            lookups={
                "ParentId": MappingLookup(
                    table="accounts", key_field="parent_id", name="ParentId"
                )
            },
        )

        query = task._query_db(mapping)

        query_columns, added_filters = _inspect_query(query)

        initialization_columns = task.session.query.mock_calls[0].args
        added_columns = []
        for call in task.session.query.mock_calls:
            name, args, kwargs = call
            if name == "add_columns":
                added_columns.extend(args)
        all_columns = initialization_columns + tuple(added_columns)

        # Validate that the column set is accurate
        assert all_columns == (
            model.sf_id,
            model.__table__.columns["name"],
            aliased.return_value.columns.sf_id,
        )

        # Validate person contact records were not filtered out
        task._can_load_person_accounts.assert_called_once_with(mapping)
        assert tuple(added_filters) == ()

    # This test should be rewritten into a light-mocking style but creating the
    # sample data is non-trivial work that might require some collaboration

    @mock.patch("cumulusci.tasks.bulkdata.query_transformers.aliased")
    def test_query_db__person_accounts_enabled__neither_account_nor_contact_mapping(
        self, aliased
    ):
        task = _make_task(
            LoadData, {"options": {"database_url": "sqlite://", "mapping": "test.yml"}}
        )
        model = mock.Mock()
        task.models = {"requests": model}
        task.metadata = mock.Mock()
        task.metadata.tables = {
            "requests_sf_ids": mock.Mock(),
            "accounts_sf_ids": mock.Mock(),
        }
        task.session = mock.Mock()
        task._can_load_person_accounts = mock.Mock(return_value=True)
        # task._filter_out_person_account_records = mock.Mock() # TODO: Replace this with a better test

        # Make mock query chainable
        task.session.query.return_value = task.session.query
        task.session.query.filter.return_value = task.session.query
        task.session.query.outerjoin.return_value = task.session.query
        task.session.query.order_by.return_value = task.session.query
        task.session.query.add_columns.return_value = task.session.query

        model.__table__ = mock.Mock()
        model.__table__.primary_key.columns.keys.return_value = ["sf_id"]
        columns = {"sf_id": mock.Mock(), "name": mock.Mock()}
        model.__table__.columns = columns

        mapping = MappingStep(
            sf_object="Request__c",
            table="requests",
            action=DataOperationType.UPDATE,
            fields={"Id": "sf_id", "Name": "name"},
            lookups={
                "ParentId": MappingLookup(
                    table="accounts", key_field="parent_id", name="ParentId"
                )
            },
        )

        query = task._query_db(mapping)
        query_columns, added_filters = _inspect_query(query)

        # Validate that the column set is accurate
        assert query_columns == (
            model.sf_id,
            model.__table__.columns["name"],
            aliased.return_value.columns.sf_id,
        )

        # Validate person contact db records had their Name updated as blank
        task._can_load_person_accounts.assert_not_called()

        # Validate person contact records were not filtered out
        assert tuple(added_filters) == ()

    def test_initialize_id_table__already_exists(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )
        task.mapping = {}
        with task._init_db():
            id_table = Table(
                "test_sf_ids",
                task.metadata,
                Column("id", Unicode(255), primary_key=True),
            )
            id_table.create()
            task._initialize_id_table({"table": "test"}, True)
            new_id_table = task.metadata.tables["test_sf_ids"]
            assert not (new_id_table is id_table)

    def test_initialize_id_table__already_exists_and_should_not_reset_table(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )
        task.mapping = {}
        with task._init_db():
            id_table = Table(
                "test_sf_ids",
                task.metadata,
                Column("id", Unicode(255), primary_key=True),
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
        task._init_db = mock.Mock(return_value=nullcontext())
        task._init_mapping = mock.Mock()
        task._execute_step = mock.Mock(
            return_value=DataOperationJobResult(
                DataOperationStatus.JOB_FAILURE, [], 0, 0
            )
        )
        task.mapping = {"Test": MappingStep(sf_object="Account")}

        with pytest.raises(BulkDataException):
            task()

    def test_process_job_results__insert_success(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.MagicMock()
        task.metadata = mock.MagicMock()
        task._initialize_id_table = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()

        local_ids = ["1"]

        step = FakeBulkAPIDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult("001111111111111", True, None)]

        mapping = MappingStep(sf_object="Account")
        with mock.patch(
            "cumulusci.tasks.bulkdata.load.sql_bulk_insert_from_records"
        ) as sql_bulk_insert_from_records:
            task._process_job_results(mapping, step, local_ids)

        task.session.connection.assert_called_once()
        task._initialize_id_table.assert_called_once_with(mapping, True)
        sql_bulk_insert_from_records.assert_called_once()
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
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task.logger = mock.Mock()

        local_ids = ["1", "2", "3", "4"]

        step = FakeBulkAPIDmlOperation(
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

        mapping = MappingStep(sf_object="Account", table="Account")
        with mock.patch(
            "cumulusci.tasks.bulkdata.load.sql_bulk_insert_from_records"
        ) as sql_bulk_insert_from_records:
            task._process_job_results(mapping, step, local_ids)

        task.session.connection.assert_called_once()
        task._initialize_id_table.assert_called_once_with(mapping, True)
        sql_bulk_insert_from_records.assert_not_called()
        task.session.commit.assert_called_once()
        assert len(task.logger.mock_calls) == 4

    def test_process_job_results__update_success(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task._initialize_id_table = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()

        local_ids = ["1"]

        step = FakeBulkAPIDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult("001111111111111", True, None)]

        mapping = MappingStep(sf_object="Account", action=DataOperationType.UPDATE)
        with mock.patch(
            "cumulusci.tasks.bulkdata.load.sql_bulk_insert_from_records"
        ) as sql_bulk_insert_from_records:
            task._process_job_results(mapping, step, local_ids)

        task.session.connection.assert_not_called()
        task._initialize_id_table.assert_not_called()
        sql_bulk_insert_from_records.assert_not_called()
        task.session.commit.assert_not_called()

    def test_process_job_results__exception_failure(self):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task._initialize_id_table = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()

        local_ids = ["1"]

        step = FakeBulkAPIDmlOperation(
            sobject="Contact",
            operation=DataOperationType.UPDATE,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult(None, False, "message")]
        step.end()

        mapping = MappingStep(sf_object="Account", action=DataOperationType.UPDATE)

        with mock.patch(
            "cumulusci.tasks.bulkdata.load.sql_bulk_insert_from_records"
        ), pytest.raises(BulkDataException) as e:
            task._process_job_results(mapping, step, local_ids)

        assert "Error on record with id" in str(e.value)
        assert "message" in str(e.value)

    def test_process_job_results__person_account_contact_ids__not_updated__mapping_action_not_insert(
        self,
    ):
        """
        Contact ID table is updated with Contact IDs for person account records
        only if all:
        ❌ mapping's action is "insert"
        ✅ mapping's sf_object is Contact
        ✅ person accounts is enabled
        ✅ an account_id_lookup is found in the mapping
        """

        # ❌ mapping's action is "insert"
        action = DataOperationType.UPDATE

        # ✅ mapping's sf_object is Contact
        sf_object = "Contact"

        # ✅ person accounts is enabled
        can_load_person_accounts = True

        # ✅ an account_id_lookup is found in the mapping
        account_id_lookup = mock.Mock()

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task._initialize_id_table = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task._can_load_person_accounts = mock.Mock(
            return_value=can_load_person_accounts
        )
        task._generate_contact_id_map_for_person_accounts = mock.Mock()

        local_ids = ["1"]

        step = FakeBulkAPIDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult("001111111111111", True, None)]

        mapping = MappingStep(
            sf_object=sf_object,
            table="Account",
            action=action,
            lookups={},
        )
        if account_id_lookup:
            mapping.lookups["AccountId"] = account_id_lookup
        with mock.patch("cumulusci.tasks.bulkdata.load.sql_bulk_insert_from_records"):
            task._process_job_results(mapping, step, local_ids)

        task._generate_contact_id_map_for_person_accounts.assert_not_called()

    def test_process_job_results__person_account_contact_ids__not_updated__sf_object_not_contact(
        self,
    ):
        """
        Contact ID table is updated with Contact IDs for person account records
        only if all:
        ✅ mapping's action is "insert"
        ❌ mapping's sf_object is Contact
        ✅ person accounts is enabled
        ✅ an account_id_lookup is found in the mapping
        """

        # ✅ mapping's action is "insert"
        action = DataOperationType.INSERT

        # ❌ mapping's sf_object is Contact
        sf_object = "Opportunity"

        # ✅ person accounts is enabled
        can_load_person_accounts = True

        # ✅ an account_id_lookup is found in the mapping
        account_id_lookup = mock.Mock()

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task.metadata = mock.MagicMock()
        task._initialize_id_table = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task._can_load_person_accounts = mock.Mock(
            return_value=can_load_person_accounts
        )
        task._generate_contact_id_map_for_person_accounts = mock.Mock()

        local_ids = ["1"]

        step = FakeBulkAPIDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult("001111111111111", True, None)]

        mapping = MappingStep(
            sf_object=sf_object,
            table="Account",
            action=action,
            lookups={},
        )
        if account_id_lookup:
            mapping.lookups["AccountId"] = account_id_lookup
        with mock.patch("cumulusci.tasks.bulkdata.load.sql_bulk_insert_from_records"):
            task._process_job_results(mapping, step, local_ids)

        task._generate_contact_id_map_for_person_accounts.assert_not_called()

    def test_process_job_results__person_account_contact_ids__not_updated__person_accounts_not_enabled(
        self,
    ):
        """
        Contact ID table is updated with Contact IDs for person account records
        only if all:
        ✅ mapping's action is "insert"
        ✅ mapping's sf_object is Contact
        ❌ person accounts is enabled
        ✅ an account_id_lookup is found in the mapping
        """

        # ✅ mapping's action is "insert"
        action = DataOperationType.INSERT

        # ✅ mapping's sf_object is Contact
        sf_object = "Contact"

        # ❌ person accounts is enabled
        can_load_person_accounts = False

        # ✅ an account_id_lookup is found in the mapping
        account_id_lookup = mock.Mock()

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.MagicMock()
        task.metadata = mock.MagicMock()
        task._initialize_id_table = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task._can_load_person_accounts = mock.Mock(
            return_value=can_load_person_accounts
        )
        task._generate_contact_id_map_for_person_accounts = mock.Mock()

        local_ids = ["1"]

        step = FakeBulkAPIDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult("001111111111111", True, None)]

        mapping = MappingStep(
            sf_object=sf_object,
            table="Account",
            action=action,
            lookups={},
        )
        if account_id_lookup:
            mapping.lookups["AccountId"] = account_id_lookup
        with mock.patch("cumulusci.tasks.bulkdata.load.sql_bulk_insert_from_records"):
            task._process_job_results(mapping, step, local_ids)

        task._generate_contact_id_map_for_person_accounts.assert_not_called()

    def test_process_job_results__person_account_contact_ids__not_updated__no_account_id_lookup(
        self,
    ):
        """
        Contact ID table is updated with Contact IDs for person account records
        only if all:
        ✅ mapping's action is "insert"
        ✅ mapping's sf_object is Contact
        ✅ person accounts is enabled
        ❌ an account_id_lookup is found in the mapping
        """

        # ✅ mapping's action is "insert"
        action = DataOperationType.INSERT

        # ✅ mapping's sf_object is Contact
        sf_object = "Contact"

        # ✅ person accounts is enabled
        can_load_person_accounts = True

        # ❌ an account_id_lookup is found in the mapping
        account_id_lookup = None

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task.metadata = mock.MagicMock()
        task._initialize_id_table = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task._can_load_person_accounts = mock.Mock(
            return_value=can_load_person_accounts
        )
        task._generate_contact_id_map_for_person_accounts = mock.Mock()

        local_ids = ["1"]

        step = FakeBulkAPIDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult("001111111111111", True, None)]

        mapping = MappingStep(
            sf_object=sf_object,
            table="Account",
            action=action,
            lookups={},
        )
        if account_id_lookup:
            mapping.lookups["AccountId"] = account_id_lookup
        with mock.patch("cumulusci.tasks.bulkdata.load.sql_bulk_insert_from_records"):
            task._process_job_results(mapping, step, local_ids)

        task._generate_contact_id_map_for_person_accounts.assert_not_called()

    def test_process_job_results__person_account_contact_ids__updated(self):
        """
        Contact ID table is updated with Contact IDs for person account records
        only if all:
        ✅ mapping's action is "insert"
        ✅ mapping's sf_object is Contact
        ✅ person accounts is enabled
        ✅ an account_id_lookup is found in the mapping
        """

        # ✅ mapping's action is "insert"
        action = DataOperationType.INSERT

        # ✅ mapping's sf_object is Contact
        sf_object = "Contact"

        # ✅ person accounts is enabled
        can_load_person_accounts = True

        # ✅ an account_id_lookup is found in the mapping
        account_id_lookup = MappingLookup(table="accounts")

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task.metadata = mock.MagicMock()
        task._initialize_id_table = mock.Mock()
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task._can_load_person_accounts = mock.Mock(
            return_value=can_load_person_accounts
        )
        task._generate_contact_id_map_for_person_accounts = mock.Mock()

        local_ids = ["1"]

        step = FakeBulkAPIDmlOperation(
            sobject="Contact",
            operation=DataOperationType.INSERT,
            api_options={},
            context=task,
            fields=[],
        )
        step.results = [DataOperationResult("001111111111111", True, None)]

        mapping = MappingStep(
            sf_object=sf_object,
            table="Account",
            action=action,
            lookups={"AccountId": account_id_lookup},
        )
        with mock.patch(
            "cumulusci.tasks.bulkdata.load.sql_bulk_insert_from_records"
        ) as sql_bulk_insert_from_records:
            task._process_job_results(mapping, step, local_ids)

        task._generate_contact_id_map_for_person_accounts.assert_called_once_with(
            mapping, mapping.lookups["AccountId"], task.session.connection.return_value
        )

        sql_bulk_insert_from_records.assert_called_with(
            connection=task.session.connection.return_value,
            table=task.metadata.tables[task._initialize_id_table.return_value],
            columns=("id", "sf_id"),
            record_iterable=task._generate_contact_id_map_for_person_accounts.return_value,
        )

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

        with pytest.raises(BulkDataException) as e:
            list(
                task._generate_results_id_map(
                    step, ["001000000000009", "001000000000010", "001000000000011"]
                )
            )

        assert "Error on record" in str(e.value)
        assert "001000000000010" in str(e.value)

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

    @mock.patch("cumulusci.tasks.bulkdata.load.get_dml_operation")
    def test_execute_step__record_type_mapping(self, dml_mock):
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        task.session = mock.Mock()
        task._load_record_types = mock.Mock()
        task._process_job_results = mock.Mock()
        task._query_db = mock.Mock()

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
        _validate_query_for_mapping_step(
            sql_path="cumulusci/tasks/bulkdata/tests/recordtypes.sql",
            mapping="cumulusci/tasks/bulkdata/tests/recordtypes.yml",
            mapping_step_name="Insert Accounts",
            expected="""SELECT accounts.sf_id AS accounts_sf_id, accounts."Name" AS "accounts_Name", "Account_rt_target_mapping".record_type_id AS "Account_rt_target_mapping_record_type_id"
                FROM accounts
                LEFT OUTER JOIN "Account_rt_mapping" ON "Account_rt_mapping".record_type_id = accounts."RecordTypeId"
                LEFT OUTER JOIN "Account_rt_target_mapping" ON "Account_rt_target_mapping".developer_name = "Account_rt_mapping".developer_name
        """,
        )

    @mock.patch("cumulusci.tasks.bulkdata.load.automap_base")
    @responses.activate
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
        task._validate_org_has_person_accounts_enabled_if_person_account_data_exists = (
            mock.Mock()
        )
        mock_describe_calls()

        task._init_task()
        task._init_mapping()
        task.mapping["Insert Households"]["fields"]["RecordTypeId"] = "RecordTypeId"
        with task._init_db():
            task._create_record_type_table.assert_called_once_with(
                "Account_rt_target_mapping"
            )
            task._validate_org_has_person_accounts_enabled_if_person_account_data_exists.assert_called_once_with()

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
                mock.call("Account", "Account_rt_target_mapping", conn),
                mock.call("Contact", "Contact_rt_target_mapping", conn),
            ]
        )

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.load.get_dml_operation")
    def test_run__autopk(self, dml_mock):
        responses.add(
            method="GET",
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id+FROM+RecordType+WHERE+SObjectType%3D%27Account%27AND+DeveloperName+%3D+%27HH_Account%27+LIMIT+1",
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
                        "set_recently_viewed": False,
                    }
                },
            )
            task.bulk = mock.Mock()
            task.sf = mock.Mock()
            step = FakeBulkAPIDmlOperation(
                sobject="Contact",
                operation=DataOperationType.INSERT,
                api_options={},
                context=task,
                fields=[],
            )
            dml_mock.return_value = step

            step.results = [
                DataOperationResult("001000000000000", True, None),
                DataOperationResult("003000000000000", True, None),
                DataOperationResult("003000000000001", True, None),
            ]

            mock_describe_calls()
            task()

            assert step.records == [
                ["TestHousehold", "1"],
                ["Test", "User", "test@example.com", "001000000000000"],
                ["Error", "User", "error@example.com", "001000000000000"],
            ], step.records

            with create_engine(task.options["database_url"]).connect() as c:
                hh_ids = next(c.execute("SELECT * from households_sf_ids"))
                assert hh_ids == ("1", "001000000000000")

    @responses.activate
    def test_run__complex_lookups(self):
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        mock_describe_calls()
        task._init_task()
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

    @responses.activate
    def test_load__inferred_keyfield_camelcase(self):
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        mock_describe_calls()
        task._init_task()
        task._init_mapping()

        class FakeModel:
            ParentId = mock.MagicMock()

        assert (
            task.mapping["Insert Accounts"]["lookups"]["ParentId"].get_lookup_key_field(
                FakeModel()
            )
            == "ParentId"
        )

    @responses.activate
    def test_load__inferred_keyfield_snakecase(self):
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        mock_describe_calls()
        task._init_task()
        task._init_mapping()

        class FakeModel:
            parent_id = mock.MagicMock()

        assert (
            task.mapping["Insert Accounts"]["lookups"]["ParentId"].get_lookup_key_field(
                FakeModel()
            )
            == "parent_id"
        )

    def test_validate_org_has_person_accounts_enabled_if_person_account_data_exists__raises_exception__account(
        self,
    ):
        """
        A BulkDataException is raised because the task will (later) attempt to load
        person account Account records, but the org does not have person accounts enabled
        which will result in an Exception from the Bulk Data API or load records in
        an unexpected state.
        - ✅ An Account or Contact object is mapped
        - ✅ The corresponding table includes an IsPersonAccount column
        - ✅ There is at least one record in the table with IsPersonAccount equals "true"
        - ✅ The org does not have person accounts enabled
        """
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        # ✅ An Account object is mapped
        mapping = MappingStep(sf_object="Account", table="account")
        model = mock.Mock()
        model.__table__ = mock.Mock()

        task.mapping = {"Mapping Step": mapping}
        task.models = {mapping["table"]: model}

        # ✅ The cooresponding table includes an IsPersonAccount column
        task._db_has_person_accounts_column = mock.Mock(return_value=True)

        # ✅ There is at least one record in the table with IsPersonAccount equals "true"
        task.session = mock.Mock()
        task.session.query.return_value = task.session.query
        task.session.query.filter.return_value = task.session.query

        assert task.session.query.first.return_value is not None

        # ✅ The org does not have person accounts enabled
        task.org_config._is_person_accounts_enabled = False

        with pytest.raises(BulkDataException):
            task._validate_org_has_person_accounts_enabled_if_person_account_data_exists()

    def test_validate_org_has_person_accounts_enabled_if_person_account_data_exists__raises_exception__contact(
        self,
    ):
        """
        A BulkDataException is raised because the task will (later) attempt to load
        person account Account records, but the org does not have person accounts enabled
        which will result in an Exception from the Bulk Data API or load records in
        an unexpected state.
        - ✅ An Account or Contact object is mapped
        - ✅ The corresponding table includes an IsPersonAccount column
        - ✅ There is at least one record in the table with IsPersonAccount equals "true"
        - ✅ The org does not have person accounts enabled
        """
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        # ✅ A Contact object is mapped
        mapping = MappingStep(sf_object="Contact", table="contact")
        model = mock.Mock()
        model.__table__ = mock.Mock()

        task.mapping = {"Mapping Step": mapping}
        task.models = {mapping["table"]: model}

        # ✅ The cooresponding table includes an IsPersonAccount column
        task._db_has_person_accounts_column = mock.Mock(return_value=True)

        # ✅ There is at least one record in the table with IsPersonAccount equals "true"
        task.session = mock.Mock()
        task.session.query.return_value = task.session.query
        task.session.query.filter.return_value = task.session.query

        assert task.session.query.first.return_value is not None

        # ✅ The org does not have person accounts enabled
        task.org_config._is_person_accounts_enabled = False

        with pytest.raises(BulkDataException):
            task._validate_org_has_person_accounts_enabled_if_person_account_data_exists()

    def test_validate_org_has_person_accounts_enabled_if_person_account_data_exists__success_if_org_has_person_accounts_enabled(
        self,
    ):
        """
        A BulkDataException is raised because the task will (later) attempt to load
        person account Account records, but the org does not have person accounts enabled
        which will result in an Exception from the Bulk Data API or load records in
        an unexpected state.
        - ✅ An Account or Contact object is mapped
        - ✅ The corresponding table includes an IsPersonAccount column
        - ✅ There is at least one record in the table with IsPersonAccount equals "true"
        - ❌ The org does not have person accounts enabled
        """
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        # ✅ An Account object is mapped
        mapping = MappingStep(table="account", sf_object="Account")
        model = mock.Mock()
        model.__table__ = mock.Mock()

        task.mapping = {"Mapping Step": mapping}
        task.models = {mapping["table"]: model}

        # ✅ The cooresponding table includes an IsPersonAccount column
        task._db_has_person_accounts_column = mock.Mock(return_value=True)

        # ✅ There is at least one record in the table with IsPersonAccount equals "true"
        task.session = mock.Mock()
        task.session.query.return_value = task.session.query
        task.session.query.filter.return_value = task.session.query

        assert task.session.query.first.return_value is not None

        # ❌ The org does has person accounts enabled
        task.org_config._is_person_accounts_enabled = True

        task._validate_org_has_person_accounts_enabled_if_person_account_data_exists()

    def test_validate_org_has_person_accounts_enabled_if_person_account_data_exists__success_if_no_person_account_records(
        self,
    ):
        """
        A BulkDataException is raised because the task will (later) attempt to load
        person account Account records, but the org does not have person accounts enabled
        which will result in an Exception from the Bulk Data API or load records in
        an unexpected state.
        - ✅ An Account or Contact object is mapped
        - ✅ The corresponding table includes an IsPersonAccount column
        - ❌ There is at least one record in the table with IsPersonAccount equals "true"
        - ✅ The org does not have person accounts enabled
        """
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        # ✅ An Account object is mapped
        mapping = MappingStep(sf_object="Account", table="account")
        model = mock.Mock()
        model.__table__ = mock.Mock()

        task.mapping = {"Mapping Step": mapping}
        task.models = {mapping["table"]: model}

        # ✅ The cooresponding table includes an IsPersonAccount column
        task._db_has_person_accounts_column = mock.Mock(return_value=True)

        # ❌ There is at least one record in the table with IsPersonAccount equals "true"
        task.session = mock.Mock()
        task.session.query.return_value = task.session.query
        task.session.query.filter.return_value = task.session.query
        task.session.query.first.return_value = None

        assert task.session.query.first.return_value is None

        # ✅ The org does has person accounts enabled
        task.org_config._is_person_accounts_enabled = True

        task._validate_org_has_person_accounts_enabled_if_person_account_data_exists()

    def test_validate_org_has_person_accounts_enabled_if_person_account_data_exists__success_if_no_person_account_column(
        self,
    ):
        """
        A BulkDataException is raised because the task will (later) attempt to load
        person account Account records, but the org does not have person accounts enabled
        which will result in an Exception from the Bulk Data API or load records in
        an unexpected state.
        - ✅ An Account or Contact object is mapped
        - ❌ The corresponding table includes an IsPersonAccount column
        - ✅ There is at least one record in the table with IsPersonAccount equals "true"
        - ✅ The org does not have person accounts enabled
        """
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        # ✅ An Account object is mapped
        mapping = MappingStep(sf_object="Account", table="account")
        model = mock.Mock()
        model.__table__ = mock.Mock()

        task.mapping = {"Mapping Step": mapping}
        task.models = {mapping["table"]: model}

        # ❌ The cooresponding table includes an IsPersonAccount column
        task._db_has_person_accounts_column = mock.Mock(return_value=False)

        # ✅ There is at least one record in the table with IsPersonAccount equals "true"
        task.session = mock.Mock()
        task.session.query.return_value = task.session.query
        task.session.query.filter.return_value = task.session.query

        assert task.session.query.first.return_value is not None

        # ✅ The org does has person accounts enabled
        task.org_config._is_person_accounts_enabled = True

        task._validate_org_has_person_accounts_enabled_if_person_account_data_exists()

    def test_validate_org_has_person_accounts_enabled_if_person_account_data_exists__success_if_no_account_or_contact_not_mapped(
        self,
    ):
        """
        A BulkDataException is raised because the task will (later) attempt to load
        person account Account records, but the org does not have person accounts enabled
        which will result in an Exception from the Bulk Data API or load records in
        an unexpected state.
        - ❌ An Account or Contact object is mapped
        - ✅ The corresponding table includes an IsPersonAccount column
        - ✅ There is at least one record in the table with IsPersonAccount equals "true"
        - ✅ The org does not have person accounts enabled
        """
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)

        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        # ❌ An Account object is mapped
        mapping = MappingStep(sf_object="CustomObject__c", table="custom_object")
        model = mock.Mock()
        model.__table__ = mock.Mock()

        task.mapping = {"Mapping Step": mapping}
        task.models = {mapping["table"]: model}

        # ✅ The cooresponding table includes an IsPersonAccount column
        task._db_has_person_accounts_column = mock.Mock(return_value=True)

        # ✅ There is at least one record in the table with IsPersonAccount equals "true"
        task.session = mock.Mock()
        task.session.query.return_value = task.session.query
        task.session.query.filter.return_value = task.session.query

        assert task.session.query.first.return_value is not None

        # ✅ The org does has person accounts enabled
        task.org_config._is_person_accounts_enabled = True

        task._validate_org_has_person_accounts_enabled_if_person_account_data_exists()

    def test_db_has_person_accounts_column(self):
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)

        for columns, expected in [
            ({}, False),
            ({"IsPersonAccount": None}, False),
            ({"IsPersonAccount": "Not None"}, True),
        ]:
            mapping = MappingStep(sf_object="Account")

            model = mock.Mock()
            model.__table__ = mock.Mock()
            model.__table__.columns = columns

            task = _make_task(
                LoadData,
                {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
            )
            task.models = {}
            task.models[mapping.table] = model

            actual = task._db_has_person_accounts_column(mapping)

            assert expected == actual, f"columns: {columns}"

    # def test_filter_out_person_account_records(self, lower):

    # This method was deleted after bb2a7aa13 because it was way too much
    # code to test too little code. We'll test Person accounts in context
    # instead.
    # Delete this comment whenever it is convenient.

    def test_generate_contact_id_map_for_person_accounts(self):
        mapping_file = "mapping-oid.yml"
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, mapping_file)

        # Set task mocks
        task = _make_task(
            LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        account_model = mock.Mock()
        contact_model = mock.Mock()
        task.models = {"accounts": account_model, "contacts": contact_model}
        task.metadata = mock.Mock()
        task.metadata.tables = {
            "accounts": mock.Mock(),
            "contacts": mock.Mock(),
            "accounts_sf_ids": mock.Mock(),
            "contacts_sf_ids": mock.Mock(),
        }
        task.session = mock.Mock()
        task.session.query.return_value = task.session.query
        task.session.query.filter.return_value = task.session.query
        task.session.query.outerjoin.return_value = task.session.query
        task.sf = mock.Mock()

        # Set model mocks
        account_model.__table__ = mock.Mock()
        account_model.__table__.primary_key.columns.keys.return_value = ["sf_id"]
        account_model.__table__.columns = {
            "id": mock.Mock(),
            "sf_id": mock.Mock(),
            "IsPersonAccount": mock.MagicMock(),
        }

        account_sf_ids_table = mock.Mock()
        account_sf_ids_table.columns = {"id": mock.Mock(), "sf_id": mock.Mock()}

        contact_model.__table__ = mock.Mock()
        contact_model.__table__.primary_key.columns.keys.return_value = ["sf_id"]
        contact_model.__table__.columns = {
            "id": mock.Mock(),
            "sf_id": mock.Mock(),
            "IsPersonAccount": mock.MagicMock(),
            "account_id": mock.Mock,
        }

        account_id_lookup = MappingLookup(
            table="accounts", key_field="account_id", name="AccountId"
        )
        account_id_lookup.aliased_table = account_sf_ids_table

        # Calculated values
        contact_id_column = getattr(
            contact_model, contact_model.__table__.primary_key.columns.keys()[0]
        )
        account_id_column = getattr(
            contact_model, account_id_lookup.get_lookup_key_field(contact_model)
        )
        account_sf_ids_table = account_id_lookup["aliased_table"]
        account_sf_id_column = account_sf_ids_table.columns["sf_id"]

        contact_mapping = MappingStep(
            sf_object="Contact",
            table="contacts",
            action=DataOperationType.UPDATE,
            fields={
                "Id": "sf_id",
                "LastName": "LastName",
                "IsPersonAccount": "IsPersonAccount",
            },
            lookups={"AccountId": account_id_lookup},
        )

        conn = mock.Mock()
        conn.execution_options.return_value = conn
        query_result = conn.execute.return_value

        def get_random_string():
            return "".join(
                [random.choice(string.ascii_letters + string.digits) for n in range(18)]
            )

        # Set records to be queried.
        chunks = [
            [
                {
                    # Table IDs
                    "id": get_random_string(),
                    # Salesforce IDs
                    "sf_id": get_random_string(),
                    "AccountId": get_random_string(),
                }
                for i in range(200)
            ],
            [
                {
                    # Table IDs
                    "id": get_random_string(),
                    # Salesforce IDs
                    "sf_id": get_random_string(),
                    "AccountId": get_random_string(),
                }
                for i in range(4)
            ],
        ]

        expected = []
        query_result.fetchmany.expected_calls = []
        task.sf.query_all.expected_calls = []
        for chunk in chunks:
            expected.extend([(record["id"], record["sf_id"]) for record in chunk])

            query_result.fetchmany.expected_calls.append(mock.call(200))

            contact_ids_by_account_sf_id = {
                record["AccountId"]: record["id"] for record in chunk
            }
            task.sf.query_all.expected_calls.append(
                mock.call(
                    "SELECT Id, AccountId FROM Contact WHERE IsPersonAccount = true AND AccountId IN ('{}')".format(
                        "','".join(contact_ids_by_account_sf_id.keys())
                    )
                )
            )

        chunks_index = 0

        def fetchmany(batch_size):
            nonlocal chunks_index

            assert 200 == batch_size

            # _generate_contact_id_map_for_person_accounts should break if fetchmany returns falsy.
            return (
                [(record["id"], record["AccountId"]) for record in chunks[chunks_index]]
                if chunks_index < len(chunks)
                else None
            )

        def query_all(query):
            nonlocal chunks_index
            chunk = chunks[chunks_index]

            contact_ids_by_account_sf_id = {
                record["AccountId"]: record["id"] for record in chunk
            }

            # query_all is called last; increment to next chunk
            chunks_index += 1

            assert (
                query
                == "SELECT Id, AccountId FROM Contact WHERE IsPersonAccount = true AND AccountId IN ('{}')".format(
                    "','".join(contact_ids_by_account_sf_id.keys())
                )
            )

            return {
                "records": [
                    {"Id": record["sf_id"], "AccountId": record["AccountId"]}
                    for record in chunk
                ]
            }

        conn.execute.return_value.fetchmany.side_effect = fetchmany
        task.sf.query_all.side_effect = query_all

        # Execute the test.
        generator = task._generate_contact_id_map_for_person_accounts(
            contact_mapping, account_id_lookup, conn
        )

        actual = [value for value in generator]

        assert expected == actual

        # Assert query executed
        task.session.query.assert_called_once_with(
            contact_id_column, account_sf_id_column
        )
        task.session.query.filter.assert_called_once()
        task.session.query.outerjoin.assert_called_once_with(
            account_sf_ids_table,
            account_sf_ids_table.columns["id"] == account_id_column,
        )
        conn.execution_options.assert_called_once_with(stream_results=True)
        conn.execute.assert_called_once_with(task.session.query.statement)

        # Assert chunks processed
        assert len(chunks) == chunks_index

        query_result.fetchmany.assert_has_calls(query_result.fetchmany.expected_calls)
        task.sf.query_all.assert_has_calls(task.sf.query_all.expected_calls)

    @responses.activate
    def test_load_memory_usage(self):
        responses.add(
            method="GET",
            url=f"https://example.com/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id+FROM+RecordType+WHERE+SObjectType%3D%27Account%27AND+DeveloperName+%3D+%27HH_Account%27+LIMIT+1",
            body=json.dumps({"records": [{"Id": "1"}]}),
            status=200,
        )

        base_path = os.path.dirname(__file__)
        sql_path = os.path.join(base_path, "testdata.sql")
        mapping_path = os.path.join(base_path, self.mapping_file)

        with temporary_dir() as d:
            tmp_sql_path = os.path.join(d, "testdata.sql")
            shutil.copyfile(sql_path, tmp_sql_path)

            class NetworklessLoadData(LoadData):
                def _query_db(self, mapping):
                    if mapping.sf_object == "Account":
                        return FakeQueryResult(
                            ((f"{i}",) for i in range(0, numrecords)), numrecords
                        )
                    elif mapping.sf_object == "Contact":
                        return FakeQueryResult(
                            (
                                (f"{i}", "Test☃", "User", "test@example.com", 0)
                                for i in range(0, numrecords)
                            ),
                            numrecords,
                        )

                def _init_task(self):
                    super()._init_task()
                    task.bulk = FakeBulkAPI()

            task = _make_task(
                NetworklessLoadData,
                {
                    "options": {
                        "sql_path": tmp_sql_path,
                        "mapping": mapping_path,
                        "set_recently_viewed": False,
                    }
                },
            )

            numrecords = 5000

            class FakeQueryResult:
                def __init__(self, results, numrecords=None):
                    self.results = results
                    if numrecords is None:
                        numrecords = len(self.results)
                    self.numrecords = numrecords

                def yield_per(self, number):
                    return self.results

                def count(self):
                    return self.numrecords

            mock_describe_calls()

            def get_results(self):
                return (
                    DataOperationResult(i, True, None) for i in range(0, numrecords)
                )

            def _job_state_from_batches(self, job_id):
                return DataOperationJobResult(
                    DataOperationStatus.SUCCESS,
                    [],
                    numrecords,
                    0,
                )

            MEGABYTE = 2**20

            # FIXME: more anlysis about the number below
            with mock.patch(
                "cumulusci.tasks.bulkdata.step.BulkJobMixin._job_state_from_batches",
                _job_state_from_batches,
            ), mock.patch(
                "cumulusci.tasks.bulkdata.step.BulkApiDmlOperation.get_results",
                get_results,
            ), assert_max_memory_usage(
                15 * MEGABYTE
            ):
                task()

    @mock.patch("cumulusci.tasks.bulkdata.load.get_org_schema")
    def test_set_viewed(self, get_org_schema):
        base_path = os.path.dirname(__file__)
        task = _make_task(
            LoadData,
            {
                "options": {
                    "sql_path": "test.sql",
                    "mapping": os.path.join(base_path, self.mapping_file),
                }
            },
        )
        queries = []

        def _query_all(query):
            queries.append(query)
            return {
                "records": [
                    {
                        "SobjectName": "Account",
                    },
                    {
                        "SobjectName": "Custom__c",
                    },
                ],
            }

        task.sf = mock.Mock()
        task.sf.query_all = _query_all
        task.mapping = {}
        task.mapping["Insert Households"] = MappingStep(sf_object="Account", fields={})
        task.mapping["Insert Custom__c"] = MappingStep(sf_object="Custom__c", fields={})

        task._set_viewed()

        get_org_schema.assert_called_with(
            task.sf,
            task.org_config,
            included_objects={"Account", "Custom__c"},
            force_recache=mock.ANY,
        )

        assert queries == [
            "SELECT SObjectName FROM TabDefinition WHERE IsCustom = true AND SObjectName IN ('Custom__c')",
            "SELECT Id FROM Account ORDER BY CreatedDate DESC LIMIT 1000 FOR VIEW",
            "SELECT Id FROM Custom__c ORDER BY CreatedDate DESC LIMIT 1000 FOR VIEW",
        ], queries

    @mock.patch("cumulusci.tasks.bulkdata.load.get_org_schema", mock.MagicMock())
    def test_set_viewed__SOQL_error_1(self):
        base_path = os.path.dirname(__file__)
        task = _make_task(
            LoadData,
            {
                "options": {
                    "sql_path": "test.sql",
                    "mapping": os.path.join(base_path, self.mapping_file),
                }
            },
        )

        def _query_all(query):
            assert 0

        task.sf = mock.Mock()
        task.sf.query_all = _query_all
        task.mapping = {}
        task.mapping["Insert Households"] = MappingStep(sf_object="Account", fields={})
        task.mapping["Insert Custom__c"] = MappingStep(sf_object="Custom__c", fields={})

        with mock.patch.object(task.logger, "warning") as warning:
            task._set_viewed()

        assert "custom tabs" in str(warning.mock_calls[0])
        assert "Account" in str(warning.mock_calls[1])

    def test_set_viewed__exception(self):
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite://",
                    "mapping": "mapping.yml",
                    "set_recently_viewed": True,
                }
            },
        )
        task._init_db = mock.Mock(return_value=nullcontext())
        task._init_mapping = mock.Mock()
        task.mapping = {}
        task.after_steps = {}

        def raise_exception():
            assert 0, "xyzzy"

        task._set_viewed = raise_exception

        with mock.patch.object(task.logger, "warning") as warning:
            task()
        assert "xyzzy" in str(warning.mock_calls[0])

    def test_no_mapping(self):
        task = _make_task(
            LoadData,
            {
                "options": {
                    "database_url": "sqlite://",
                }
            },
        )
        task._init_db = mock.Mock(return_value=nullcontext())
        with pytest.raises(TaskOptionsError, match="Mapping file path required"):
            task()

    @mock.patch("cumulusci.tasks.bulkdata.load.validate_and_inject_mapping")
    def test_mapping_contains_extra_sobjects(self, _):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            LoadData,
            {
                "options": {
                    "mapping": mapping_path,
                    "database_url": "sqlite://",
                }
            },
        )
        with pytest.raises(BulkDataException):
            task()

    @responses.activate
    def test_mapping_file_with_explicit_IsPersonAccount(self, caplog):
        mock_describe_calls()
        base_path = Path(__file__).parent
        mapping_path = base_path / "person_accounts_minimal.yml"
        task = _make_task(
            LoadData,
            {
                "options": {
                    "mapping": mapping_path,
                    "database_url": "sqlite://",
                }
            },
        )

        task._init_task()
        task._init_mapping()


class TestLoadDataIntegrationTests:
    # bulk API not supported by VCR yet
    @pytest.mark.needs_org()
    def test_error_result_counting__multi_batches(
        self, create_task, cumulusci_test_repo_root
    ):
        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root / "datasets/bad_sample.sql",
                "mapping": cumulusci_test_repo_root / "datasets/mapping.yml",
                "ignore_row_errors": True,
            },
        )
        with mock.patch("cumulusci.tasks.bulkdata.step.DEFAULT_BULK_BATCH_SIZE", 3):
            task()
        ret = task.return_values["step_results"]
        assert ret["Account"]["total_row_errors"] == 1
        assert ret["Contact"]["total_row_errors"] == 1
        assert ret["Opportunity"]["total_row_errors"] == 2
        expected = {
            "Account": {
                "sobject": "Account",
                "status": "Row failure",
                "job_errors": [],
                "records_processed": 2,
                "total_row_errors": 1,
                "record_type": None,
            },
            "Contact": {
                "sobject": "Contact",
                "status": "Row failure",
                "job_errors": [],
                "records_processed": 2,
                "total_row_errors": 1,
                "record_type": None,
            },
            "Opportunity": {
                "sobject": "Opportunity",
                "status": "Row failure",
                "job_errors": [],
                "records_processed": 4,
                "total_row_errors": 2,
                "record_type": None,
            },
        }
        assert json.loads(json.dumps(ret)) == expected, json.dumps(ret)

    # bulk API not supported by VCR yet
    @pytest.mark.needs_org()
    def test_bulk_batch_size(self, create_task):
        base_path = os.path.dirname(__file__)
        sql_path = os.path.join(base_path, "testdata.sql")
        mapping_path = os.path.join(base_path, "mapping_simple.yml")

        orig_batch = BulkApiDmlOperation._batch
        counts = {}

        def _batch(self, records, n, *args, **kwargs):
            records = list(records)
            if records == [["TestHousehold"]]:
                counts.setdefault("Account", []).append(n)
            elif records[0][1] == "User":
                counts.setdefault("Contact", []).append(n)
            else:
                assert 0, "Data in SQL must have changed!"
            records = list(records)
            return orig_batch(self, records, n, *args, **kwargs)

        with mock.patch(
            "cumulusci.tasks.bulkdata.step.BulkApiDmlOperation._batch",
            _batch,
        ):
            task = create_task(
                LoadData,
                {
                    "sql_path": sql_path,
                    "mapping": mapping_path,
                    "ignore_row_errors": True,
                },
            )
            task()
            assert counts == {"Account": [10000], "Contact": [1]}

    @pytest.mark.needs_org()
    def test_recreate_set_recent_bug(
        self, sf, create_task, cumulusci_test_repo_root, org_config
    ):
        with get_org_schema(sf, org_config, included_objects=["Account"]):
            pass

        task = create_task(
            LoadData,
            {
                "sql_path": cumulusci_test_repo_root / "datasets/sample.sql",
                "mapping": cumulusci_test_repo_root / "datasets/mapping.yml",
                "ignore_row_errors": True,
            },
        )
        task.logger = mock.Mock()
        results = task()
        assert results["set_recently_viewed"] == [
            ("Account", None),
            ("Contact", None),
            ("Opportunity", None),
        ]


def _validate_query_for_mapping_step(sql_path, mapping, mapping_step_name, expected):
    """Validate the text of a SQL query"""
    task = _make_task(
        LoadData,
        {
            "options": {
                "sql_path": sql_path,
                "mapping": mapping,
            }
        },
    )
    with mock.patch(
        "cumulusci.tasks.bulkdata.load.validate_and_inject_mapping"
    ), mock.patch.object(task, "sf", create=True):
        task._init_mapping()
    with task._init_db():
        query = task._query_db(task.mapping[mapping_step_name])

    def normalize(query):
        return str(query).replace(" ", "").replace("\n", "").replace("\t", "").lower()

    actual = normalize(query)
    expected = normalize(expected)
    if actual != expected:
        print("ACTUAL", actual)
        print("EXPECT", expected)
        print("QUERY", query)
    assert actual == expected


def _inspect_query(query_mock: mock.Mock):
    """Figure out what was done to a mocked query"""
    initialization_columns = query_mock.mock_calls[0].args
    added_columns = []
    added_filters = []
    for call in query_mock.mock_calls:
        name, args, kwargs = call
        if name == "add_columns":
            added_columns.extend(args)
        elif name == "filter":
            added_filters.extend(args)
    query_columns = initialization_columns + tuple(added_columns)
    return query_columns, added_filters
