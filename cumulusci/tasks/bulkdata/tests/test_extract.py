import os
from contextlib import contextmanager
from datetime import date, timedelta
from tempfile import TemporaryDirectory
from unittest import mock

import pytest
import responses
from sqlalchemy import create_engine

from cumulusci.core.exceptions import (
    BulkDataException,
    ConfigError,
    CumulusCIException,
    TaskOptionsError,
)
from cumulusci.tasks.bulkdata import ExtractData
from cumulusci.tasks.bulkdata.mapping_parser import MappingLookup, MappingStep
from cumulusci.tasks.bulkdata.step import (
    BaseQueryOperation,
    DataApi,
    DataOperationJobResult,
    DataOperationStatus,
    DataOperationType,
)
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.tests.util import (
    assert_max_memory_usage,
    mock_describe_calls,
    mock_salesforce_client,
)
from cumulusci.utils import temporary_dir


@contextmanager
def mock_extract_jobs(task, extracted_records):
    def _job_state_from_batches(self, job_id):
        return DataOperationJobResult(
            DataOperationStatus.SUCCESS,
            [],
            10,
            0,
        )

    def get_results(self):
        return extracted_records[self.sobject]

    with mock.patch(
        "cumulusci.tasks.bulkdata.step.BulkApiQueryOperation.get_results",
        get_results,
    ), mock.patch(
        "cumulusci.tasks.bulkdata.step.BulkJobMixin._job_state_from_batches",
        _job_state_from_batches,
    ):
        yield


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


class MockScalableBulkQueryOperation(MockBulkQueryOperation):
    def query(self):
        self.job_id = "JOB"
        self.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], self.result_len, 0
        )


class TestExtractData:

    mapping_file_v1 = "mapping_v1.yml"
    mapping_file_v2 = "mapping_v2.yml"
    mapping_file_poly = "mapping_poly.yml"
    mapping_file_poly_wrong = "mapping_poly_wrong.yml"
    mapping_file_poly_incomplete = "mapping_poly_incomplete.yml"
    mapping_file_vanilla = "mapping_vanilla_sf.yml"

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run__person_accounts_disabled(self, query_op_mock):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()
        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "testdata.db")

            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{tmp_db_path}",
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
            mock_query_households.results = [["1", "None"]]
            mock_query_contacts.results = [
                ["2", "First", "Last", "test@example.com", "1"]
            ]

            query_op_mock.side_effect = [mock_query_households, mock_query_contacts]

            task()

            with create_engine(task.options["database_url"]).connect() as conn:
                household = next(conn.execute("select * from households"))
                assert household.sf_id == "1"
                assert not hasattr(household, "IsPersonAccount")
                assert household.record_type == "HH_Account"

                contact = next(conn.execute("select * from contacts"))
                assert contact.sf_id == "2"
                assert not hasattr(contact, "IsPersonAccount")
                assert contact.household_id == "1"

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run__person_accounts_enabled(self, query_op_mock):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()

        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "testdata.db")

            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{tmp_db_path}",
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
                query="SELECT Id, Name IsPersonAccount FROM Account",
            )
            mock_query_contacts = MockBulkQueryOperation(
                sobject="Contact",
                api_options={},
                context=task,
                query="SELECT Id, FirstName, LastName, Email, IsPersonAccount, AccountId FROM Contact",
            )
            mock_query_households.results = [["1", "None", "false"]]
            mock_query_contacts.results = [
                ["2", "First", "Last", "test@example.com", "true", "1"]
            ]

            query_op_mock.side_effect = [mock_query_households, mock_query_contacts]

            task()
            with create_engine(task.options["database_url"]).connect() as conn:

                household = next(conn.execute("select * from households"))
                assert household.sf_id == "1"
                assert household.IsPersonAccount == "false"
                assert household.record_type == "HH_Account"

                contact = next(conn.execute("select * from contacts"))
                assert contact.sf_id == "2"
                assert contact.IsPersonAccount == "true"
                assert contact.household_id == "1"

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run__sql(self, query_op_mock):
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
                ["2", "First☃", "Last", "test@example.com", "1"]
            ]
            query_op_mock.side_effect = [mock_query_households, mock_query_contacts]

            with mock.patch(
                "cumulusci.tasks.bulkdata.extract.create_engine", wraps=create_engine
            ) as ce_mock:
                task()

            assert os.path.exists("testdata.sql")
            assert ce_mock.mock_calls[0][1][0].endswith(
                "temp_db.db"
            ), ce_mock.mock_calls[0][1][0]
            assert ce_mock.mock_calls[0][1][0].startswith(
                "sqlite:///"
            ), ce_mock.mock_calls[0][1][0]

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run__v2__person_accounts_disabled(self, query_op_mock):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v2)
        mock_describe_calls()

        with TemporaryDirectory() as t:
            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{t}/temp_db",  # in memory
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
            mock_query_contacts.results = [
                ["2", "First", "Last", "test@example.com", "1"]
            ]

            query_op_mock.side_effect = [mock_query_households, mock_query_contacts]

            task()
            with create_engine(task.options["database_url"]).connect() as conn:
                household = next(conn.execute("select * from households"))
                assert household.name == "TestHousehold"
                assert not hasattr(household, "IsPersonAccount")
                assert household.record_type == "HH_Account"

                contact = next(conn.execute("select * from contacts"))
                assert contact.household_id == "Account-1"
                assert not hasattr(contact, "IsPersonAccount")

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run__v2__person_accounts_enabled(self, query_op_mock):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v2)
        mock_describe_calls()
        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "testdata.db")
            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{tmp_db_path}",
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

            query_op_mock.side_effect = [mock_query_households, mock_query_contacts]

            task()
            with create_engine(task.options["database_url"]).connect() as conn:
                household = next(conn.execute("select * from households"))
                assert household.name == "TestHousehold"
                assert household.IsPersonAccount == "false"
                assert household.record_type == "HH_Account"

                contact = next(conn.execute("select * from contacts"))
                assert contact.household_id == "Account-1"
                assert contact.IsPersonAccount == "true"

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run__poly__polymorphic_lookups(self, query_op_mock):
        """Test for polymorphic lookups"""
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_poly)
        mock_describe_calls()

        with temporary_dir() as t:
            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{t}/temp_poly.db",  # in memory
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
            mock_query_events = MockBulkQueryOperation(
                sobject="Event",
                api_options={},
                context=task,
                query="SELECT Id, LastName, WhoId FROM Event",
            )
            mock_query_households.results = [["abc123", "TestHousehold"]]
            mock_query_contacts.results = [
                ["def456", "First", "Last", "test@example.com", "abc123"]
            ]
            mock_query_events.results = [
                ["ijk789", "Last1", "abc123"],
                ["lmn010", "Last2", "def456"],
            ]

            query_op_mock.side_effect = [
                mock_query_households,
                mock_query_contacts,
                mock_query_events,
            ]
            task()
            with create_engine(task.options["database_url"]).connect() as conn:
                household = next(conn.execute("select * from households"))
                assert household.name == "TestHousehold"
                assert not hasattr(household, "IsPersonAccount")
                assert household.record_type == "HH_Account"

                contact = next(conn.execute("select * from contacts"))
                assert contact.household_id == "Account-1"
                assert not hasattr(contact, "IsPersonAccount")

                events = conn.execute("select * from events").fetchall()
                assert events[0].who_id == "Account-1"
                assert events[1].who_id == "Contact-1"

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run__poly__wrong_mapping(self, query_op_mock):
        """Test for polymorphic lookups with wrong mapping file
        (missing table)"""
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_poly_wrong)
        mock_describe_calls()

        with temporary_dir() as t:
            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{t}/temp_poly.db",  # in memory
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
            mock_query_events = MockBulkQueryOperation(
                sobject="Event",
                api_options={},
                context=task,
                query="SELECT Id, LastName, WhoId FROM Event",
            )
            mock_query_households.results = [["abc123", "TestHousehold"]]
            mock_query_contacts.results = [
                ["def456", "First", "Last", "test@example.com", "abc123"]
            ]
            mock_query_events.results = [
                ["ijk789", "Last1", "abc123"],
                ["lmn010", "Last2", "def456"],
            ]

            query_op_mock.side_effect = [
                mock_query_households,
                mock_query_contacts,
                mock_query_events,
            ]
            with pytest.raises(CumulusCIException) as e:
                task()

            assert "The following tables are missing in the mapping file:" in str(
                e.value
            )

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run__poly__incomplete_mapping(self, query_op_mock):
        """Test for polymorphic lookups with incomplete mapping file"""
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_poly_incomplete)
        mock_describe_calls()

        with temporary_dir() as t:
            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{t}/temp_poly.db",  # in memory
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
            mock_query_events = MockBulkQueryOperation(
                sobject="Event",
                api_options={},
                context=task,
                query="SELECT Id, LastName, WhoId FROM Event",
            )
            mock_query_households.results = [["abc123", "TestHousehold"]]
            mock_query_events.results = [
                ["ijk789", "Last1", "abc123"],
                ["lmn010", "Last2", "def456"],
            ]

            query_op_mock.side_effect = [mock_query_households, mock_query_events]
            with pytest.raises(ConfigError) as e:
                task()

            assert "Total mapping operations" in str(e.value)
            assert "do not match total non-empty rows" in str(e.value)

    @mock.patch("cumulusci.tasks.bulkdata.extract.log_progress")
    def test_import_results__oid_as_pk(self, log_mock):
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        mapping = MappingStep(
            sf_object="Opportunity",
            fields={"Id": "sf_id", "Name": "Name"},
            lookups={"AccountId": MappingLookup(table="Account", name="AccountId")},
        )
        step = mock.Mock()
        task.session = mock.Mock()
        task.metadata = mock.MagicMock()

        with mock.patch(
            "cumulusci.tasks.bulkdata.extract.sql_bulk_insert_from_records"
        ) as sql_bulk_insert_from_records:
            task._import_results(mapping, step)

        task.session.connection.assert_called_once_with()
        step.get_results.assert_called_once_with()
        sql_bulk_insert_from_records.assert_called_once_with(
            connection=task.session.connection.return_value,
            table=task.metadata.tables[mapping.table],
            columns=["sf_id", "Name", "AccountId"],
            record_iterable=log_mock.return_value,
        )

    @responses.activate
    def test_import_results__no_columns(self):  # , query_op_mock):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()

        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        mapping = MappingStep(
            sf_object="Opportunity",
            table="Opportunity",
            fields={},
            lookups={},
        )
        step = mock.Mock()
        step.get_results.return_value = [[1], [2]]
        task.session = mock.Mock()
        task._init_task()
        task._init_mapping()
        task.mapping["Opportunity"] = mapping
        with task._init_db():
            task._import_results(mapping, step)
            output_Opportunties = list(
                task.session.execute("select * from Opportunity")
            )
            assert output_Opportunties == [("Opportunity-1",), ("Opportunity-2",)]

    @responses.activate
    def test_import_results__relative_dates(self):
        mock_describe_calls()
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        mapping = MappingStep(
            sf_object="Opportunity",
            fields={"Id": "sf_id", "CloseDate": "CloseDate"},
            anchor_date="2020-07-01",
        )
        step = mock.Mock()
        step.get_results.return_value = iter(
            [["006000000000001", (date.today() + timedelta(days=9)).isoformat()]]
        )
        task.session = mock.Mock()
        task.metadata = mock.MagicMock()
        task._init_task()
        with mock.patch(
            "cumulusci.tasks.bulkdata.extract.sql_bulk_insert_from_records"
        ) as sql_bulk_insert_from_records:
            task._import_results(mapping, step)

        task.session.connection.assert_called_once_with()
        step.get_results.assert_called_once_with()
        sql_bulk_insert_from_records.assert_called_once_with(
            connection=task.session.connection.return_value,
            table=task.metadata.tables[mapping.table],
            columns=["sf_id", "CloseDate"],
            record_iterable=mock.ANY,
        )

        result = list(
            sql_bulk_insert_from_records.call_args_list[0][1]["record_iterable"]
        )
        assert result == [["006000000000001", "2020-07-10"]]

    def test_import_results__record_type_mapping(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "recordtypes.yml")
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._extract_record_types = mock.Mock()
        task.metadata = mock.MagicMock()
        task.session = mock.Mock()
        task.org_config._is_person_accounts_enabled = False

        step = mock.Mock()
        step.get_results.return_value = [["000000000000001", "Test", "012000000000000"]]

        mapping = MappingStep(
            sf_object="Account",
            fields={"Name": "Name", "RecordTypeId": "RecordTypeId"},
            lookups={},
            table="accounts",
        )
        with mock.patch(
            "cumulusci.tasks.bulkdata.extract.sql_bulk_insert_from_records_incremental",
            return_value=[None, None],
        ):
            task._import_results(
                mapping,
                step,
            )
        task._extract_record_types.assert_called_once_with(
            "Account",
            mapping.get_source_record_type_table(),
            task.session.connection.return_value,
            task.org_config._is_person_accounts_enabled,
        )

    def test_import_results__person_account_name_stripped(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "recordtypes.yml")
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._extract_record_types = mock.Mock()
        task.session = mock.Mock()
        task.metadata = mock.MagicMock()
        task.org_config._is_person_accounts_enabled = True

        step = mock.Mock()
        step.get_results.return_value = [
            ["000000000000001", "Person Account", "012000000000001", "true"],
            ["000000000000002", "Business Account", "012000000000002", "false"],
        ]

        with mock.patch(
            "cumulusci.tasks.bulkdata.extract.sql_bulk_insert_from_records"
        ) as sql_bulk_insert_from_records:
            task._import_results(
                MappingStep(
                    sf_object="Account",
                    fields={
                        "Id": "sf_id",
                        "Name": "Name",
                        "RecordTypeId": "RecordTypeId",
                        "IsPersonAccount": "IsPersonAccount",
                    },
                    lookups={},
                ),
                step,
            )

        sql_bulk_insert_from_records.assert_called()
        args, kwargs = sql_bulk_insert_from_records.call_args_list[0]

        records = [record for record in kwargs["record_iterable"]]

        assert [
            ["000000000000001", "", "012000000000001", "true"],
            ["000000000000002", "Business Account", "012000000000002", "false"],
        ] == records

    @responses.activate
    def test_map_autopks(self):
        mock_describe_calls()
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
        task._convert_lookups_to_id = mock.Mock()
        task.metadata = mock.MagicMock()

        task._init_task()
        task._init_mapping()
        task._map_autopks()

        task._convert_lookups_to_id.assert_called_once_with(
            task.mapping["Insert Contacts"], ["AccountId"]
        )
        task.metadata.tables.__getitem__.return_value.drop.assert_has_calls(
            [mock.call(), mock.call()]
        )
        task.metadata.tables.__getitem__.assert_has_calls(
            [mock.call("contacts_sf_ids"), mock.call("households_sf_ids")],
            any_order=True,
        )

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
            "Account": MappingStep(sf_object="Account"),
            "Opportunity": MappingStep(sf_object="Opportunity"),
        }

        task.session.query.return_value.filter.return_value.count.return_value = 0
        task.session.query.return_value.filter.return_value.update.return_value.rowcount = (
            0
        )
        task._convert_lookups_to_id(
            MappingStep(
                sf_object="Opportunity",
                lookups={"AccountId": MappingLookup(table="Account", name="AccountId")},
            ),
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
            "Account": MappingStep(sf_object="Account"),
            "Opportunity": MappingStep(sf_object="Opportunity"),
        }
        task.session.query.return_value.filter.return_value.update.side_effect = (
            NotImplementedError
        )

        item = mock.Mock()

        task.session.query.return_value.join.return_value = [(item, "1")]
        task.session.query.return_value.filter.return_value.count.return_value = 1

        task._convert_lookups_to_id(
            MappingStep(
                sf_object="Opportunity",
                lookups={"AccountId": MappingLookup(table="Account", name="AccountId")},
            ),
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
        mapping = MappingStep(
            sf_object="Account",
            fields={"Name": "Name", "Id": "sf_id"},
            lookups={},
            table="accounts",
        )
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

        with pytest.raises(BulkDataException):
            task()

    def test_create_table__record_type_mapping(self):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        task.mapping = {
            "Insert Accounts": MappingStep(
                sf_object="Account",
                table="accounts",
                fields={"Name": "Name", "RecordTypeId": "RecordTypeId"},
                lookups={},
            ),
            "Insert Other Accounts": MappingStep(
                sf_object="Account",
                fields={"Name": "Name", "RecordTypeId": "RecordTypeId"},
                lookups={},
                table="accounts_2",
            ),
        }
        task.org_config._is_person_accounts_enabled = False

        def create_table_mock(table_name):
            task.models[table_name] = mock.Mock()

        task._create_record_type_table = mock.Mock(side_effect=create_table_mock)
        with task._init_db():
            task._create_record_type_table.assert_called_once_with("Account_rt_mapping")

    @mock.patch("cumulusci.tasks.bulkdata.extract.create_table")
    @mock.patch("cumulusci.tasks.bulkdata.extract.Table")
    @mock.patch("cumulusci.tasks.bulkdata.extract.mapper")
    def test_create_table__autopk(self, mapper_mock, table_mock, create_mock):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        mapping = MappingStep(
            sf_object="Account",
            fields={"Name": "Name"},
            table="accounts",
        )
        task.models = {}
        task.metadata = mock.Mock()
        task.org_config._is_person_accounts_enabled = False

        task._create_table(mapping)

        create_mock.assert_called_once_with(mapping, task.metadata)
        assert len(table_mock.mock_calls) == 1

        assert "accounts" in task.models
        assert mapping.get_sf_id_table() in task.models

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

    def test_init_db(self):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        task._create_tables = mock.Mock()
        with task._init_db():
            assert task.models == {}
            assert task.session.query

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

        task._init_task()
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

        task._init_task()
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

        t._init_task()
        t._init_mapping()

        validate_and_inject_mapping.assert_called_once_with(
            mapping=t.mapping,
            sf=t.sf,
            namespace=t.project_config.project__package__namespace,
            data_operation=DataOperationType.QUERY,
            inject_namespaces=True,
            drop_missing=True,
            org_has_person_accounts_enabled=t.org_config._is_person_accounts_enabled,
        )

    def test_soql_for_mapping(self):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        mapping = MappingStep(
            sf_object="Contact",
            fields={"Id": "sf_id", "Test__c": "Test"},
        )
        assert task._soql_for_mapping(mapping) == "SELECT Id, Test__c FROM Contact"

        mapping = MappingStep(
            sf_object="Contact",
            record_type="Devel",
            fields={"Id": "sf_id", "Test__c": "Test"},
        )
        assert (
            task._soql_for_mapping(mapping)
            == "SELECT Id, Test__c FROM Contact WHERE RecordType.DeveloperName = 'Devel'"
        )

    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run_query(self, query_op_mock):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        task._import_results = mock.Mock()
        query_op_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 1, 0
        )

        task._run_query("SELECT Id FROM Contact", MappingStep(sf_object="Contact"))

        query_op_mock.assert_called_once_with(
            sobject="Contact",
            fields=["Id"],
            api=DataApi.SMART,
            api_options={},
            context=task,
            query="SELECT Id FROM Contact",
        )
        query_op_mock.return_value.query.assert_called_once_with()
        task._import_results.assert_called_once_with(
            MappingStep(sf_object="Contact"), query_op_mock.return_value
        )

    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run_query__no_results(self, query_op_mock):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        task._import_results = mock.Mock()
        query_op_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], 0, 0
        )

        task._run_query("SELECT Id FROM Contact", MappingStep(sf_object="Contact"))

        query_op_mock.assert_called_once_with(
            sobject="Contact",
            fields=["Id"],
            api=DataApi.SMART,
            api_options={},
            context=task,
            query="SELECT Id FROM Contact",
        )
        query_op_mock.return_value.query.assert_called_once_with()
        task._import_results.assert_not_called()

    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_run_query__failure(self, query_op_mock):
        task = _make_task(
            ExtractData, {"options": {"database_url": "sqlite:///", "mapping": ""}}
        )
        query_op_mock.return_value.job_result = DataOperationJobResult(
            DataOperationStatus.JOB_FAILURE, [], 1, 0
        )

        with pytest.raises(BulkDataException):
            task._run_query("SELECT Id FROM Contact", MappingStep(sf_object="Contact"))

    def test_init_options__missing_output(self):
        with pytest.raises(TaskOptionsError):
            _make_task(ExtractData, {"options": {}})

    @mock.patch("cumulusci.tasks.bulkdata.extract.log_progress")
    def test_extract_respects_key_field(self, log_mock):
        task = _make_task(
            ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": "mapping.yml"}},
        )

        mapping = MappingStep(
            sf_object="Opportunity",
            table="Opportunity",
            fields={"Id": "sf_id", "Name": "Name"},
            lookups={
                "AccountId": MappingLookup(
                    table="Account", key_field="account_id", name="AccountId"
                )
            },
        )
        step = mock.Mock()
        task.session = mock.Mock()
        task.metadata = mock.MagicMock()

        with mock.patch(
            "cumulusci.tasks.bulkdata.extract.sql_bulk_insert_from_records"
        ) as sql_bulk_insert_from_records:
            task._import_results(mapping, step)

        task.session.connection.assert_called_once_with()
        step.get_results.assert_called_once_with()
        sql_bulk_insert_from_records.assert_called_once_with(
            connection=task.session.connection.return_value,
            table=task.metadata.tables["Opportunity"],
            columns=["sf_id", "Name", "account_id"],
            record_iterable=log_mock.return_value,
        )

    @responses.activate
    @mock.patch("cumulusci.tasks.bulkdata.extract.get_query_operation")
    def test_extract_memory_usage(self, step_mock):
        with TemporaryDirectory() as t:
            base_path = os.path.dirname(__file__)
            mapping_path = os.path.join(base_path, self.mapping_file_v1)
            mock_describe_calls()

            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{t}/foo.db",  # tempdir database
                        "mapping": mapping_path,
                    }
                },
            )
            task.bulk = mock.Mock()
            task.sf = mock.Mock()
            task.org_config._is_person_accounts_enabled = False

            mock_query_households = MockScalableBulkQueryOperation(
                sobject="Account",
                api_options={},
                context=task,
                query="SELECT Id FROM Account",
            )
            mock_query_contacts = MockScalableBulkQueryOperation(
                sobject="Contact",
                api_options={},
                context=task,
                query="SELECT Id, FirstName, LastName, Email, AccountId FROM Contact",
            )
            mock_query_households.results = ([str(num)] for num in range(1, 20000))
            mock_query_households.result_len = 20000
            mock_query_contacts.results = [
                ["2", "First", "Last", "test@example.com", "1"]
            ]
            mock_query_contacts.result_len = 1

            step_mock.side_effect = [mock_query_households, mock_query_contacts]

            with assert_max_memory_usage(15 * 10**6):
                task()

    @responses.activate
    def test_import_results__autopk(self, create_task_fixture):
        mock_describe_calls()
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_vanilla)
        with temporary_dir() as d:
            task = create_task_fixture(
                ExtractData,
                {"database_url": f"sqlite:///{d}/temp.db", "mapping": mapping_path},
            )

            extracted_records = {
                # ['Name', 'Description', 'BillingStreet', 'BillingCity', 'BillingState', 'BillingPostalCode', 'BillingCountry', 'ParentId', 'ShippingStreet', 'ShippingCity', 'ShippingState', 'ShippingPostalCode', 'ShippingCountry', 'Phone', 'Fax', 'Website', 'NumberOfEmployees', 'AccountNumber', 'Site', 'Type', 'IsPersonAccount']
                "Account": [
                    ["001002", "Account1"] + [""] * 20 + [False],
                    ["001003", "Account2"] + [""] * 20 + [False],
                ],
                # Salutation|FirstName|LastName|Email|Phone|MobilePhone|OtherPhone|HomePhone|Title|Birthdate|MailingStreet|MailingCity|MailingState|MailingPostalCode|MailingCountry|AccountId
                "Contact": [
                    ["002001", "", "Bob 1", "Barker 2"] + [""] * 4,
                    ["002002", "", "Sam 2", "Smith 2"] + [""] * 4,
                ],  # id|Name|StageName|CloseDate|Amount|AccountId|ContactId|record_type
                "Opportunity": [
                    [
                        "0003001",
                        "Dickenson Mobile Generators",
                        "Qualification",
                        "2020-07-18",
                        "15000.0",
                        "001003",
                        "002001",
                    ]
                ],
            }
            with mock_extract_jobs(task, extracted_records), mock_salesforce_client(
                task
            ):
                task()
            with create_engine(task.options["database_url"]).connect() as conn:
                output_accounts = list(conn.execute("select * from Account"))
                assert output_accounts[0][0:2] == ("Account-1", "Account1")
                assert output_accounts[1][0:2] == ("Account-2", "Account2")
                assert len(output_accounts) == 2
                output_opportunities = list(conn.execute("select * from Opportunity"))

                assert output_opportunities[0].AccountId == "Account-2"
                assert output_opportunities[0].ContactId == "Contact-1"

    def test_run_soql_filter(self):
        """This test case is to verify when soql_filter is specified with valid filter in the mapping yml"""

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()
        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "testdata.db")

            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{tmp_db_path}",
                        "mapping": mapping_path,
                    }
                },
            )

            mapping = MappingStep(
                sf_object="Contact",
                fields={"Id": "Id", "Name": "Name"},
                record_type="Business",
                soql_filter="Name = 'John Doe'",
            )

            soql = task._soql_for_mapping(mapping)
            assert (
                "WHERE RecordType.DeveloperName = 'Business' AND Name = 'John Doe'"
                in soql
            ), "Filter should be applied on Name and DeveloperName"

    def test_run_soql_filter_where_specified(self):
        """This test case is to verify when soql_filter is specified with mapping yml with WHERE keyword in it"""

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()
        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "testdata.db")

            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{tmp_db_path}",
                        "mapping": mapping_path,
                    }
                },
            )

            mapping = MappingStep(
                sf_object="Contact",
                fields={"Id": "Id", "Name": "Name"},
                record_type="Business",
                soql_filter=" wHeRe Name = 'John Doe'",
            )

            soql = task._soql_for_mapping(mapping)
            assert (
                "WHERE RecordType.DeveloperName = 'Business' AND Name = 'John Doe'"
                in soql
            ), "Filter should be applied on Name and RecordType"

    def test_run_soql_filter_no_record_type(self):
        """This test case is to verify when soql_filter is specified in mapping yml file but no record_type"""

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file_v1)
        mock_describe_calls()
        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "testdata.db")

            task = _make_task(
                ExtractData,
                {
                    "options": {
                        "database_url": f"sqlite:///{tmp_db_path}",
                        "mapping": mapping_path,
                    }
                },
            )

            mapping = MappingStep(
                sf_object="Contact",
                fields={"Id": "Id", "Name": "Name"},
                soql_filter=" wHeRe Name = 'John Doe'",
            )

            soql = task._soql_for_mapping(mapping)
            assert (
                "WHERE Name = 'John Doe'" in soql
            ), "filter should be applied just on name"
            assert (
                "DeveloperName" not in soql
            ), "DeveloperName should not appear in the soql query as it is missing in mapping"
