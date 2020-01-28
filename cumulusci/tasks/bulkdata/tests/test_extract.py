import os
import responses
import unittest

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode

from unittest import mock

from cumulusci.core.exceptions import TaskOptionsError, BulkDataException
from cumulusci.tasks import bulkdata
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.utils import temporary_dir


class TestExtractDataWithSFIds(unittest.TestCase):

    mapping_file = "mapping_v1.yml"
    HOUSEHOLD_QUERY_RESULT = b'"Id"\n1\n'
    CONTACT_QUERY_RESULT = b'"Id",AccountId\n2,1\n'

    @responses.activate
    def test_run(self):
        api = mock.Mock()
        api.endpoint = "http://api"
        api.headers.return_value = {}
        api.create_query_job.side_effect = ["1", "2"]
        api.query.side_effect = ["3", "4"]
        api.get_query_batch_result_ids.side_effect = [["5"], ["6"]]
        responses.add(
            responses.GET,
            "http://api/job/1/batch/3/result/5",
            body=self.HOUSEHOLD_QUERY_RESULT,
        )
        responses.add(
            responses.GET,
            "http://api/job/2/batch/4/result/6",
            body=self.CONTACT_QUERY_RESULT,
        )

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)

        task = _make_task(
            bulkdata.ExtractData,
            {
                "options": {
                    "database_url": "sqlite://",  # in memory
                    "mapping": mapping_path,
                }
            },
        )

        def _init_class():
            task.bulk = api

        task._init_class = _init_class
        task()

        household = task.session.query(task.models["households"]).one()
        self.assertEqual("1", household.sf_id)
        self.assertEqual("HH_Account", household.record_type)
        contact = task.session.query(task.models["contacts"]).one()
        self.assertEqual("2", contact.sf_id)
        self.assertEqual("1", contact.household_id)

    def test_import_results__record_type_mapping(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "recordtypes.yml")
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._extract_record_types = mock.Mock()
        task._sql_bulk_insert_from_records = mock.Mock()
        task.session = mock.Mock()

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

    @mock.patch("cumulusci.tasks.bulkdata.extract.create_table")
    @mock.patch("cumulusci.tasks.bulkdata.extract.mapper")
    def test_create_table(self, mapper_mock, create_mock):
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": ""}},
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

    def test_create_table__already_exists(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        db_path = os.path.join(base_path, "testdata.db")
        task = _make_task(
            bulkdata.ExtractData,
            {
                "options": {
                    "database_url": f"sqlite:///{db_path}",
                    "mapping": mapping_path,
                }
            },
        )
        with self.assertRaises(BulkDataException):
            task()

    def test_create_table__record_type_mapping(self):
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": ""}},
        )
        task.mappings = {
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
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": ""}},
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
        task._create_table(mapping)

        assert mapping["sf_id_table"] == "accounts_sf_id"
        create_mock.assert_called_once_with(mapping, task.metadata)
        table_mock.assert_any_call(
            "accounts_sf_id",
            task.metadata,
            Column("id", Integer(), primary_key=True, autoincrement=True),
            Column("sf_id", Unicode(24)),
        )

        assert "accounts" in task.models

    def test_create_tables(self):
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": ""}},
        )
        task.mappings = {1: "test", 2: "foo", 3: "bar"}
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
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": ""}},
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

    def test_init_mapping(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": mapping_path}},
        )

        task._init_mapping()
        assert "Insert Households" in task.mappings

    def test_fields_for_mapping(self):
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": ""}},
        )
        assert task._fields_for_mapping(
            {"oid_as_pk": False, "fields": {"Test__c": "Test"}}
        ) == ["Id", "Test__c"]
        assert task._fields_for_mapping(
            {"oid_as_pk": True, "fields": {"Id": "sf_id", "Test__c": "Test"}}
        ) == ["Id", "Test__c"]

    def test_soql_for_mapping(self):
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": ""}},
        )
        mapping = {
            "sf_object": "Contact",
            "oid_as_pk": True,
            "fields": {"Id": "sf_id", "Test__c": "Test"},
        }
        assert task._soql_for_mapping(mapping) == "SELECT Id, Test__c FROM Contact"

        mapping = {
            "sf_object": "Contact",
            "record_type": "Devel",
            "oid_as_pk": True,
            "fields": {"Id": "sf_id", "Test__c": "Test"},
        }
        assert (
            task._soql_for_mapping(mapping)
            == "SELECT Id, Test__c FROM Contact WHERE RecordType.DeveloperName = 'Devel'"
        )

    @mock.patch("cumulusci.tasks.bulkdata.extract.BulkApiQueryStep")
    def test_run_query(self, step_mock):
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite:///", "mapping": ""}},
        )

        task._run_query()

    def test_run_query__failure(self):
        raise NotImplementedError

    @responses.activate
    def test_run__sql(self):
        api = mock.Mock()
        api.endpoint = "http://api"
        api.headers.return_value = {}
        api.create_query_job.side_effect = ["1", "2"]
        api.query.side_effect = ["3", "4"]
        api.get_query_batch_result_ids.side_effect = [["5"], ["6"]]
        responses.add(
            responses.GET,
            "http://api/job/1/batch/3/result/5",
            body=self.HOUSEHOLD_QUERY_RESULT,
        )
        responses.add(
            responses.GET,
            "http://api/job/2/batch/4/result/6",
            body=self.CONTACT_QUERY_RESULT,
        )

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)

        with temporary_dir():
            task = _make_task(
                bulkdata.ExtractData,
                {"options": {"sql_path": "testdata.sql", "mapping": mapping_path}},
            )

            def _init_class():
                task.bulk = api

            task._init_class = _init_class
            task()

            assert os.path.exists("testdata.sql")

    def test_init_options__missing_output(self):
        with self.assertRaises(TaskOptionsError):
            _make_task(bulkdata.ExtractData, {"options": {}})


class TestExtractDataWithoutSFIds(unittest.TestCase):

    mapping_file = "mapping_v2.yml"
    HOUSEHOLD_QUERY_RESULT = b'"Id",Name\n"foo","TestHousehold"\n'
    CONTACT_QUERY_RESULT = b'"Id",AccountId,\n2,"foo"\n'

    @responses.activate
    def test_run(self):
        api = mock.Mock()
        api.endpoint = "http://api"
        api.headers.return_value = {}
        api.create_query_job.side_effect = ["1", "2"]
        api.query.side_effect = ["3", "4"]
        api.get_query_batch_result_ids.side_effect = [["5"], ["6"]]
        responses.add(
            responses.GET,
            "http://api/job/1/batch/3/result/5",
            body=self.HOUSEHOLD_QUERY_RESULT,
        )
        responses.add(
            responses.GET,
            "http://api/job/2/batch/4/result/6",
            body=self.CONTACT_QUERY_RESULT,
        )

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)

        task = _make_task(
            bulkdata.ExtractData,
            {
                "options": {
                    "database_url": "sqlite://",  # in memory
                    "mapping": mapping_path,
                }
            },
        )

        def _init_class():
            task.bulk = api

        task._init_class = _init_class
        task()

        household = task.session.query(task.models["households"]).one()
        self.assertEqual("TestHousehold", household.name)
        self.assertEqual("HH_Account", household.record_type)
        contact = task.session.query(task.models["contacts"]).one()
        self.assertEqual("1", contact.household_id)
