import os
import unittest
from unittest import mock

from cumulusci.core.exceptions import TaskOptionsError, BulkDataException
from cumulusci.tasks.bulkdata import ExtractData
from cumulusci.tasks.bulkdata.step import (
    BaseQueryOperation,
    DataOperationStatus,
    DataOperationJobResult,
    DataOperationType,
)
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.tasks.bulkdata.tests.test_utils import mock_describe_calls
from cumulusci.utils import temporary_dir
from cumulusci.tasks.bulkdata.mapping_parser import MappingLookup, MappingStep

import responses


class MockBulkQueryOperation(BaseQueryOperation):
    def __init__(self, *, sobject, api_options, context, query):
        super().__init__(
            sobject=sobject, api_options=api_options, context=context, query=query
        )
        self.results = []

    def query(self):
        self.job_id = "JOB"
        self.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], len(self.results), 0
        )

    def get_results(self):
        return iter(self.results)


class TestExtractData(unittest.TestCase):

    mapping_file_v1 = "mapping_v1.yml"
    mapping_file_v2 = "mapping_v2.yml"

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.BulkApiQueryOperation")
    def test_run__person_accounts_disabled(self, step_mock):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()

        task = _make_task(
            ExtractData,
            {
                "options": {
                    "database_url": "sqlite://",  # in memory
                    "mapping": mapping_path,
                }
            },
        )
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task.org_config._is_person_accounts_enabled = False

        mock_query_households = MockBulkQueryOperation(
            sobject="Account",
            api_options={},
            context=task,
            query="SELECT Id FROM Account",
        )
        mock_query_contacts = MockBulkQueryOperation(
            sobject="Contact",
            api_options={},
            context=task,
            query="SELECT Id, FirstName, LastName, Email, AccountId FROM Contact",
        )
        mock_query_households.results = [["1"]]
        mock_query_contacts.results = [["2", "First", "Last", "test@example.com", "1"]]

        step_mock.side_effect = [mock_query_households, mock_query_contacts]

        task()

        household = task.session.query(task.models["households"]).one()
        self.assertEqual("1", household.sf_id)
        self.assertFalse(hasattr(household, "IsPersonAccount"))
        self.assertEqual("HH_Account", household.record_type)

        contact = task.session.query(task.models["contacts"]).one()
        self.assertEqual("2", contact.sf_id)
        self.assertFalse(hasattr(contact, "IsPersonAccount"))
        self.assertEqual("1", contact.household_id)

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.BulkApiQueryOperation")
    def test_run__person_accounts_enabled(self, step_mock):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()

        task = _make_task(
            ExtractData,
            {
                "options": {
                    "database_url": "sqlite://",  # in memory
                    "mapping": mapping_path,
                }
            },
        )
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task.org_config._is_person_accounts_enabled = True

        mock_query_households = MockBulkQueryOperation(
            sobject="Account",
            api_options={},
            context=task,
            query="SELECT Id, IsPersonAccount FROM Account",
        )
        mock_query_contacts = MockBulkQueryOperation(
            sobject="Contact",
            api_options={},
            context=task,
            query="SELECT Id, FirstName, LastName, Email, IsPersonAccount, AccountId FROM Contact",
        )
        mock_query_households.results = [["1", "false"]]
        mock_query_contacts.results = [
            ["2", "First", "Last", "test@example.com", "true", "1"]
        ]

        step_mock.side_effect = [mock_query_households, mock_query_contacts]

        task()

        household = task.session.query(task.models["households"]).one()
        self.assertEqual("1", household.sf_id)
        self.assertEqual("false", household.IsPersonAccount)
        self.assertEqual("HH_Account", household.record_type)

        contact = task.session.query(task.models["contacts"]).one()
        self.assertEqual("2", contact.sf_id)
        self.assertEqual("true", contact.IsPersonAccount)
        self.assertEqual("1", contact.household_id)

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.BulkApiQueryOperation")
    def test_run__sql(self, step_mock):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()

        with temporary_dir():
            task = _make_task(
                ExtractData,
                {"options": {"sql_path": "testdata.sql", "mapping": mapping_path}},
            )
            task.bulk = mock.Mock()
            task.sf = mock.Mock()
            task.org_config._is_person_accounts_enabled = False

            mock_query_households = MockBulkQueryOperation(
                sobject="Account",
                api_options={},
                context=task,
                query="SELECT Id FROM Account",
            )
            mock_query_contacts = MockBulkQueryOperation(
                sobject="Contact",
                api_options={},
                context=task,
                query="SELECT Id, FirstName, LastName, Email, AccountId FROM Contact",
            )
            mock_query_households.results = [["1"]]
            mock_query_contacts.results = [
                ["2", "First", "Last", "test@example.com", "1"]
            ]
            step_mock.side_effect = [mock_query_households, mock_query_contacts]

            task()

            assert os.path.exists("testdata.sql")

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.BulkApiQueryOperation")
    def test_run__v2__person_accounts_disabled(self, step_mock):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v2)
        mock_describe_calls()

        task = _make_task(
            ExtractData,
            {
                "options": {
                    "database_url": "sqlite://",  # in memory
                    "mapping": mapping_path,
                }
            },
        )
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task.org_config._is_person_accounts_enabled = False

        mock_query_households = MockBulkQueryOperation(
            sobject="Account",
            api_options={},
            context=task,
            query="SELECT Id, Name FROM Account",
        )
        mock_query_contacts = MockBulkQueryOperation(
            sobject="Contact",
            api_options={},
            context=task,
            query="SELECT Id, FirstName, LastName, Email, AccountId FROM Contact",
        )
        mock_query_households.results = [["1", "TestHousehold"]]
        mock_query_contacts.results = [["2", "First", "Last", "test@example.com", "1"]]

        step_mock.side_effect = [mock_query_households, mock_query_contacts]

        task()
        household = task.session.query(task.models["households"]).one()
        assert household.name == "TestHousehold"
        assert not hasattr(household, "IsPersonAccount")
        assert household.record_type == "HH_Account"

        contact = task.session.query(task.models["contacts"]).one()
        assert contact.household_id == "1"
        assert not hasattr(contact, "IsPersonAccount")

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.BulkApiQueryOperation")
    def test_run__v2__person_accounts_enabled(self, step_mock):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v2)
        mock_describe_calls()

        task = _make_task(
            ExtractData,
            {
                "options": {
                    "database_url": "sqlite://",  # in memory
                    "mapping": mapping_path,
                }
            },
        )
        task.bulk = mock.Mock()
        task.sf = mock.Mock()
        task.org_config._is_person_accounts_enabled = True

        mock_query_households = MockBulkQueryOperation(
            sobject="Account",
            api_options={},
            context=task,
            query="SELECT Id, Name, IsPersonAccount FROM Account",
        )
        mock_query_contacts = MockBulkQueryOperation(
            sobject="Contact",
            api_options={},
            context=task,
            query="SELECT Id, FirstName, LastName, Email, IsPersonAccount, AccountId FROM Contact",
        )
        mock_query_households.results = [["1", "TestHousehold", "false"]]
        mock_query_contacts.results = [
            ["2", "First", "Last", "test@example.com", "true", "1"]
        ]

        step_mock.side_effect = [mock_query_households, mock_query_contacts]

        task()
        household = task.session.query(task.models["households"]).one()
        assert household.name == "TestHousehold"
        assert household.IsPersonAccount == "false"
        assert household.record_type == "HH_Account"

        contact = task.session.query(task.models["contacts"]).one()
        assert contact.household_id == "1"
        assert contact.IsPersonAccount == "true"

    @mock.patch("cumulusci.tasks.bulkdata.extract.log_progress")
    def test_import_results__oid_as_pk(self, log_mock):
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        mapping = {
            "sf_object": "Opportunity",
            "table": "Opportunity",
            "oid_as_pk": True,
            "fields": {"Id": "sf_id", "Name": "Name"},
            "lookups": {"AccountId": MappingLookup(table="Account", name="AccountId")},
        }
        step = mock.Mock()
        task.session = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()

        task._import_results(mapping, step)

        task.session.connection.assert_called_once_with()
        step.get_results.assert_called_once_with()
        task._sql_bulk_insert_from_records.assert_called_once_with(
            connection=task.session.connection.return_value,
            table="Opportunity",
            columns=["sf_id", "Name", "AccountId"],
            record_iterable=log_mock.return_value,
        )

    @mock.patch("cumulusci.tasks.bulkdata.extract.csv.reader")
    def test_import_results__autopk(self, csv_mock):
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        mapping = {
            "sf_object": "Opportunity",
            "table": "Opportunity",
            "sf_id_table": "Opportunity_sf_ids",
            "oid_as_pk": False,
            "fields": {"Name": "Name"},
            "lookups": {"AccountId": MappingLookup(table="Account", name="AccountId")},
        }
        step = mock.Mock()
        step.get_results.return_value = iter(
            [["111", "Test Opportunity", "1"], ["222", "Test Opportunity 2", "1"]]
        )
        task.session = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()
        task._convert_lookups_to_id = mock.Mock()
        task._import_results(mapping, step)

        task.session.connection.assert_called_once_with()
        step.get_results.assert_called_once_with()
        task._sql_bulk_insert_from_records.assert_has_calls(
            [
                mock.call(
                    connection=task.session.connection.return_value,
                    table="Opportunity",
                    columns=["Name", "AccountId"],
                    record_iterable=csv_mock.return_value,
                ),
                mock.call(
                    connection=task.session.connection.return_value,
                    table="Opportunity_sf_ids",
                    columns=["sf_id"],
                    record_iterable=csv_mock.return_value,
                ),
            ]
        )
        task._convert_lookups_to_id.assert_called_once_with(mapping, ["AccountId"])

    def test_import_results__no_columns(self):
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        mapping = {
            "sf_object": "Opportunity",
            "table": "Opportunity",
            "oid_as_pk": False,
            "fields": {},
            "lookups": {},
        }
        step = mock.Mock()
        task.session = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()

        task._import_results(mapping, step)

        task.session.connection.assert_called_once_with()
        task._sql_bulk_insert_from_records.assert_not_called()

    def test_import_results__record_type_mapping(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "recordtypes.yml")
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._extract_record_types = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()
        task.session = mock.Mock()
        task.org_config._is_person_accounts_enabled = False

        step = mock.Mock()
        step.get_results.return_value = [["000000000000001", "Test", "012000000000000"]]

        task._import_results(
            {
                "sf_object": "Account",
                "record_type_table": "test_rt",
                "fields": {"Name": "Name", "RecordTypeId": "RecordTypeId"},
                "lookups": {},
                "table": "accounts",
                "sf_id_table": "test_ids",
                "oid_as_pk": False,
            },
            step,
        )
        task._extract_record_types.assert_called_once_with(
            "Account", "test_rt", task.session.connection.return_value
        )

    def test_import_results__person_account_name_stripped(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "recordtypes.yml")
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._extract_record_types = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()
        task.session = mock.Mock()
        task.org_config._is_person_accounts_enabled = True

        step = mock.Mock()
        step.get_results.return_value = [
            ["000000000000001", "Person Account", "012000000000001", "true"],
            ["000000000000002", "Business Account", "012000000000002", "false"],
        ]

        task._import_results(
            {
                "sf_object": "Account",
                "record_type_table": "test_rt",
                "fields": {
                    "Name": "Name",
                    "RecordTypeId": "RecordTypeId",
                    "IsPersonAccount": "IsPersonAccount",
                },
                "lookups": {},
                "table": "accounts",
                "sf_id_table": "test_ids",
                "oid_as_pk": True,  # So we can extract record_iterable from _sql_bulk_insert_from_records
            },
            step,
        )

        task._sql_bulk_insert_from_records.assert_called()
        args, kwargs = task._sql_bulk_insert_from_records.call_args_list[0]

        records = [record for record in kwargs["record_iterable"]]

        assert [
            ["000000000000001", "", "012000000000001", "true"],
            ["000000000000002", "Business Account", "012000000000002", "false"],
        ] == records

    def test_convert_lookups_to_id(self):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )

        task.session = mock.Mock()
        task.models = {
            "Account": mock.Mock(),
            "Account_sf_ids": mock.Mock(),
            "Opportunity": mock.Mock(),
            "Opportunity_sf_ids": mock.Mock(),
        }
        task.mapping = {
            "Account": {"table": "Account", "sf_id_table": "Account_sf_ids"},
            "Opportunity": {
                "table": "Opportunity",
                "sf_id_table": "Opportunity_sf_ids",
            },
        }

        task._convert_lookups_to_id(
            {
                "sf_object": "Opportunity",
                "table": "Opportunity",
                "sf_id_table": "Opportunity_sf_ids",
                "lookups": {
                    "AccountId": MappingLookup(table="Account", name="AccountId")
                },
            },
            ["AccountId"],
        )

        task.session.query.return_value.filter.return_value.update.assert_called_once_with(
            {task.models["Opportunity"].AccountId: task.models["Account_sf_ids"].id},
            synchronize_session=False,
        )
        task.session.commit.assert_called_once_with()

    def test_convert_lookups_to_id__sqlite(self):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )

        task.session = mock.Mock()
        task.models = {
            "Account": mock.Mock(),
            "Account_sf_ids": mock.Mock(),
            "Opportunity": mock.Mock(),
            "Opportunity_sf_ids": mock.Mock(),
        }
        task.mapping = {
            "Account": {"table": "Account", "sf_id_table": "Account_sf_ids"},
            "Opportunity": {
                "table": "Opportunity",
                "sf_id_table": "Opportunity_sf_ids",
            },
        }
        task.session.query.return_value.filter.return_value.update.side_effect = (
            NotImplementedError
        )

        item = mock.Mock()

        task.session.query.return_value.join.return_value = [(item, "1")]

        task._convert_lookups_to_id(
            {
                "sf_object": "Opportunity",
                "table": "Opportunity",
                "sf_id_table": "Opportunity_sf_ids",
                "lookups": {
                    "AccountId": MappingLookup(table="Account", name="AccountId")
                },
            },
            ["AccountId"],
        )

        task.session.bulk_update_mappings.assert_called_once_with(
            task.models["Opportunity"], [{"id": item.id, "AccountId": "1"}]
        )
        task.session.commit.assert_called_once_with()

    @mock.patch("cumulusci.tasks.bulkdata.extract.create_table")
    @mock.patch("cumulusci.tasks.bulkdata.extract.mapper")
    def test_create_table(self, mapper_mock, create_mock):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        mapping = {
            "sf_object": "Account",
            "fields": {"Name": "Name"},
            "lookups": {},
            "table": "accounts",
            "sf_id_table": "test_ids",
            "oid_as_pk": True,
        }
        task.models = {}
        task.metadata = mock.Mock()
        task._create_table(mapping)
        create_mock.assert_called_once_with(mapping, task.metadata)

        assert "accounts" in task.models

    @responses.activate
    def test_create_table__already_exists(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        db_path = os.path.join(base_path, "testdata.db")
        mock_describe_calls()
        task = _make_task(
            ExtractData,
            {
                "options": {
                    "database_url": f"sqlite:///{db_path}",
                    "mapping": mapping_path,
                }
            },
        )
        task.org_config._is_person_accounts_enabled = False

        with self.assertRaises(BulkDataException):
            task()

    def test_create_table__record_type_mapping(self):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        task.mapping = {
            "Insert Accounts": {
                "sf_object": "Account",
                "fields": {"Name": "Name", "RecordTypeId": "RecordTypeId"},
                "lookups": {},
                "table": "accounts",
                "sf_id_table": "test_ids",
                "oid_as_pk": False,
            },
            "Insert Other Accounts": {
                "sf_object": "Account",
                "fields": {"Name": "Name", "RecordTypeId": "RecordTypeId"},
                "lookups": {},
                "table": "accounts_2",
                "sf_id_table": "test_ids_2",
                "oid_as_pk": False,
            },
        }
        task.org_config._is_person_accounts_enabled = False

        def create_table_mock(table_name):
            task.models[table_name] = mock.Mock()

        task._create_record_type_table = mock.Mock(side_effect=create_table_mock)
        task._init_db()
        task._create_record_type_table.assert_called_once_with("Account_rt_mapping")

    @mock.patch("cumulusci.tasks.bulkdata.extract.create_table")
    @mock.patch("cumulusci.tasks.bulkdata.extract.Table")
    @mock.patch("cumulusci.tasks.bulkdata.extract.mapper")
    def test_create_table__autopk(self, mapper_mock, table_mock, create_mock):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        mapping = {
            "sf_object": "Account",
            "fields": {"Name": "Name"},
            "lookups": {},
            "table": "accounts",
            "sf_id_table": "test_ids",
            "oid_as_pk": False,
        }
        task.models = {}
        task.metadata = mock.Mock()
        task.org_config._is_person_accounts_enabled = False

        task._create_table(mapping)

        assert mapping["sf_id_table"] == "accounts_sf_id"
        create_mock.assert_called_once_with(mapping, task.metadata)
        assert len(table_mock.mock_calls) == 1

        assert "accounts" in task.models
        assert "accounts_sf_id" in task.models

    def test_create_tables(self):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        task.mapping = {1: "test", 2: "foo", 3: "bar"}
        task.metadata = mock.Mock()
        task._create_table = mock.Mock()

        task._create_tables()

        task._create_table.assert_has_calls(
            [mock.call("test"), mock.call("foo"), mock.call("bar")]
        )
        task.metadata.create_all.assert_called_once_with()

    @mock.patch("cumulusci.tasks.bulkdata.extract.create_engine")
    @mock.patch("cumulusci.tasks.bulkdata.extract.MetaData")
    @mock.patch("cumulusci.tasks.bulkdata.extract.automap_base")
    @mock.patch("cumulusci.tasks.bulkdata.extract.create_session")
    def test_init_db(self, session_mock, automap_mock, metadata_mock, engine_mock):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        task._create_tables = mock.Mock()
        task._init_db()

        assert task.models == {}
        engine_mock.assert_called_once_with("sqlite:///")
        metadata_mock.assert_called_once_with()
        assert task.engine == engine_mock.return_value
        assert task.metadata.bind == task.engine
        task._create_tables.assert_called_once_with()
        automap_mock.assert_called_once_with(
            bind=engine_mock.return_value, metadata=metadata_mock.return_value
        )
        automap_mock.return_value.prepare.assert_called_once_with(
            engine_mock.return_value, reflect=True
        )
        session_mock.assert_called_once_with(
            bind=engine_mock.return_value, autocommit=False
        )
        assert task.session == session_mock.return_value

    def assert_person_accounts_in_mapping(
        self, mapping, org_has_person_accounts_enabled
    ):
        for step in mapping.values():
            if step["sf_object"] in ("Account", "Contact"):
                assert org_has_person_accounts_enabled == (
                    "IsPersonAccount" in step["fields"]
                )

    @responses.activate
    def test_init_mapping(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": mapping_path}},
        )
        task.org_config._is_person_accounts_enabled = False

        task._init_mapping()
        assert "Insert Households" in task.mapping

        # Person Accounts should not be added to mapping
        self.assert_person_accounts_in_mapping(task.mapping, False)

    @responses.activate
    def test_init_mapping_org_has_person_accounts_enabled(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": mapping_path}},
        )
        task.org_config._is_person_accounts_enabled = True

        task._init_mapping()
        assert "Insert Households" in task.mapping

        # Person Accounts should not be added to mapping
        self.assert_person_accounts_in_mapping(task.mapping, True)

    @mock.patch("cumulusci.tasks.bulkdata.extract.validate_and_inject_mapping")
    def test_init_mapping_passes_options_to_validate(self, validate_and_inject_mapping):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        t = _make_task(
            ExtractData,
            {
                "options": {
                    "database_url": "sqlite:///",
                    "mapping": mapping_path,
                    "inject_namespaces": True,
                    "drop_missing_schema": True,
                }
            },
        )
        t.org_config._is_person_accounts_enabled = True

        t._init_mapping()

        validate_and_inject_mapping.assert_called_once_with(
            mapping=t.mapping,
            org_config=t.org_config,
            namespace=t.project_config.project__package__namespace,
            data_operation=DataOperationType.QUERY,
            inject_namespaces=True,
            drop_missing=True,
            org_has_person_accounts_enabled=t.org_config._is_person_accounts_enabled,
        )

    def test_fields_for_mapping(self):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        assert task._fields_for_mapping(
            {"oid_as_pk": False, "fields": {"Test__c": "Test"}}
        ) == ["Id", "Test__c"]
        assert task._fields_for_mapping(
            {"oid_as_pk": True, "fields": {"Id": "sf_id", "Test__c": "Test"}}
        ) == ["Id", "Test__c"]

    def test_soql_for_mapping(self):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        mapping = MappingStep(
            sf_object="Contact",
            oid_as_pk=True,
            fields={"Id": "sf_id", "Test__c": "Test"},
        )
        assert task._soql_for_mapping(mapping) == "SELECT Id, Test__c FROM Contact"

        mapping = MappingStep(
            sf_object="Contact",
            record_type="Devel",
            oid_as_pk=True,
            fields={"Id": "sf_id", "Test__c": "Test"},
        )
        assert (
            task._soql_for_mapping(mapping)
            == "SELECT Id, Test__c FROM Contact WHERE RecordType.DeveloperName = 'Devel'"
        )

    @mock.patch("cumulusci.tasks.bulkdata.extract.BulkApiQueryOperation")
    def test_run_query(self, step_mock):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        task._import_results = mock.Mock()
        step_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 1, 0
        )

        task._run_query("SELECT Id FROM Contact", {"sf_object": "Contact"})

        step_mock.assert_called_once_with(
            sobject="Contact",
            api_options={},
            context=task,
            query="SELECT Id FROM Contact",
        )
        step_mock.return_value.query.assert_called_once_with()
        task._import_results.assert_called_once_with(
            {"sf_object": "Contact"}, step_mock.return_value
        )

    @mock.patch("cumulusci.tasks.bulkdata.extract.BulkApiQueryOperation")
    def test_run_query__no_results(self, step_mock):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        task._import_results = mock.Mock()
        step_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        task._run_query("SELECT Id FROM Contact", {"sf_object": "Contact"})

        step_mock.assert_called_once_with(
            sobject="Contact",
            api_options={},
            context=task,
            query="SELECT Id FROM Contact",
        )
        step_mock.return_value.query.assert_called_once_with()
        task._import_results.assert_not_called()

    @mock.patch("cumulusci.tasks.bulkdata.extract.BulkApiQueryOperation")
    def test_run_query__failure(self, step_mock):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        step_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.JOB_FAILURE, [], 1, 0
        )

        with self.assertRaises(BulkDataException):
            task._run_query("SELECT Id FROM Contact", {"sf_object": "Contact"})

    def test_init_options__missing_output(self):
        with self.assertRaises(TaskOptionsError):
            _make_task(ExtractData, {"options": {}})

    @mock.patch("cumulusci.tasks.bulkdata.extract.log_progress")
    def test_extract_respects_key_field(self, log_mock):
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        mapping = {
            "sf_object": "Opportunity",
            "table": "Opportunity",
            "oid_as_pk": True,
            "fields": {"Id": "sf_id", "Name": "Name"},
            "lookups": {
                "AccountId": MappingLookup(
                    table="Account", key_field="account_id", name="AccountId"
                )
            },
        }
        step = mock.Mock()
        task.session = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()

        task._import_results(mapping, step)

        task.session.connection.assert_called_once_with()
        step.get_results.assert_called_once_with()
        task._sql_bulk_insert_from_records.assert_called_once_with(
            connection=task.session.connection.return_value,
            table="Opportunity",
            columns=["sf_id", "Name", "account_id"],
            record_iterable=log_mock.return_value,
        )
