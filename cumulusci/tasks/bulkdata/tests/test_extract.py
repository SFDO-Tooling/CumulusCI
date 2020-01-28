import io
import os
import responses
import unittest

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

    def test_sql_bulk_insert_from_csv__postgres(self):
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
        task.session = mock.Mock()
        conn = mock.Mock()
        conn.dialect.name = "psycopg2"
        cursor = mock.Mock()
        cursor.__enter__ = lambda self: self
        cursor.__exit__ = mock.Mock()
        conn.connection.cursor.return_value = cursor
        task._sql_bulk_insert_from_csv(
            conn, "table", ["column"], mock.sentinel.data_file
        )
        cursor.copy_expert.assert_called_once_with(
            "COPY table (column) FROM STDIN WITH (FORMAT CSV)", mock.sentinel.data_file
        )
        task.session.flush.assert_called_once()

    def test_import_results__no_results(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._sql_bulk_insert_from_csv = mock.Mock()
        result_file = io.BytesIO(b"Records not found for this query")
        task._import_results({}, result_file, None)
        task._sql_bulk_insert_from_csv.assert_not_called()

    def test_import_results__no_columns(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._sql_bulk_insert_from_csv = mock.Mock()
        result_file = io.BytesIO(b"")
        task._import_results({"fields": {}, "lookups": {}}, result_file, None)
        task._sql_bulk_insert_from_csv.assert_not_called()

    def test_import_results__record_type_mapping(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "recordtypes.yml")
        task = _make_task(
            bulkdata.ExtractData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._extract_record_types = mock.Mock()
        task._sql_bulk_insert_from_csv = mock.Mock()
        task.session = mock.Mock()
        result_file = io.BytesIO(
            b"Id,Name,RecordTypeId\n000000000000001,Test,012000000000000"
        )
        conn = mock.Mock()
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
            result_file,
            conn,
        )
        task._extract_record_types.assert_called_once_with("Account", "test_rt", conn)

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
