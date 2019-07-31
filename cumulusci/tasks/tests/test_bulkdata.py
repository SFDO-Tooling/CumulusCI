from datetime import datetime
import io
import json
import os
import shutil
import unittest
from collections import OrderedDict

from sqlalchemy import Column
from sqlalchemy import Table
from sqlalchemy import types
from sqlalchemy import Unicode
import mock
import responses

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import BulkDataException
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.utils import ordered_yaml_load
from cumulusci.tasks import bulkdata
from cumulusci.tests.util import DummyOrgConfig
from cumulusci.utils import temporary_dir


class TestEpochType(unittest.TestCase):
    def test_process_bind_param(self):
        obj = bulkdata.EpochType()
        dt = datetime(1970, 1, 1, 0, 0, 1)
        result = obj.process_bind_param(dt, None)
        self.assertEqual(1000, result)

    def test_process_result_value(self):
        obj = bulkdata.EpochType()

        # Non-None value
        result = obj.process_result_value(1000, None)
        self.assertEqual(datetime(1970, 1, 1, 0, 0, 1), result)

        # None value
        result = obj.process_result_value(None, None)
        self.assertEqual(None, result)

    def test_setup_epoch(self):
        column_info = {"type": types.DateTime()}
        bulkdata.setup_epoch(mock.Mock(), mock.Mock(), column_info)
        self.assertIsInstance(column_info["type"], bulkdata.EpochType)


BULK_DELETE_QUERY_RESULT = b"Id\n003000000000001".splitlines()
BULK_DELETE_RESPONSE = b'<root xmlns="http://ns"><id>4</id></root>'
BULK_BATCH_RESPONSE = '<root xmlns="http://ns"><batch><state>{}</state></batch></root>'


def _make_task(task_class, task_config):
    task_config = TaskConfig(task_config)
    global_config = BaseGlobalConfig()
    project_config = BaseProjectConfig(global_config, config={"noyaml": True})
    keychain = BaseProjectKeychain(project_config, "")
    project_config.set_keychain(keychain)
    org_config = DummyOrgConfig(
        {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
    )
    return task_class(project_config, task_config, org_config)


@mock.patch("cumulusci.tasks.bulkdata.time.sleep", mock.Mock())
class TestDeleteData(unittest.TestCase):
    @responses.activate
    def test_run(self):
        api = mock.Mock()
        api.endpoint = "http://api"
        api.jobNS = "http://ns"
        api.create_query_job.return_value = query_job = "1"
        api.query.return_value = query_batch = "2"
        api.is_batch_done.side_effect = [False, True, False, True]
        api.get_all_results_for_query_batch.return_value = [BULK_DELETE_QUERY_RESULT]
        api.create_job.return_value = delete_job = "3"
        api.headers.return_value = {}
        responses.add(
            method="POST",
            url="http://api/job/3/batch",
            body=BULK_DELETE_RESPONSE,
            status=200,
        )
        api.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        responses.add(
            method="GET",
            url="http://api/job/3/batch",
            body=BULK_BATCH_RESPONSE.format("InProgress"),
            status=200,
        )
        responses.add(
            method="GET",
            url="http://api/job/3/batch",
            body=BULK_BATCH_RESPONSE.format("Completed"),
            status=200,
        )

        task = _make_task(bulkdata.DeleteData, {"options": {"objects": "Contact"}})

        def _init_class():
            task.bulk = api

        task._init_class = _init_class
        task()

        api.create_query_job.assert_called_once_with("Contact", contentType="CSV")
        api.query.assert_called_once_with(query_job, "select Id from Contact")
        api.is_batch_done.assert_has_calls(
            [mock.call(query_batch, query_job), mock.call(query_batch, query_job)]
        )
        api.create_job.assert_called_once_with("Contact", "delete")
        api.close_job.assert_has_calls([mock.call(query_job), mock.call(delete_job)])

    def test_create_job__no_records(self):
        task = _make_task(bulkdata.DeleteData, {"options": {"objects": "Contact"}})
        task._query_salesforce_for_records_to_delete = mock.Mock(return_value=[])
        task.logger = mock.Mock()
        task._create_job("Contact")
        task.logger.info.assert_called_with(
            "  No Contact objects found, skipping delete"
        )

    def test_parse_job_state(self):
        task = _make_task(bulkdata.DeleteData, {"options": {"objects": "Contact"}})
        api = mock.Mock()
        api.jobNS = "http://ns"
        task.bulk = api
        self.assertEqual(
            ("InProgress", None),
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>InProgress</state></batch>"
                "  <batch><state>Failed</state><stateMessage>test</stateMessage></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )
        self.assertEqual(
            ("Failed", ["test"]),
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>Failed</state><stateMessage>test</stateMessage></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )
        self.assertEqual(
            ("Completed", None),
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>Completed</state></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )
        self.assertEqual(
            ("Aborted", None),
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>Not Processed</state></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )

    @responses.activate
    def test_upload_batches__error(self):
        task = _make_task(bulkdata.DeleteData, {"options": {"objects": "Contact"}})
        api = mock.Mock()
        api.endpoint = "http://api"
        api.headers.return_value = {}
        api.raise_error.side_effect = Exception

        def _init_class():
            task.bulk = api

        task._init_class = _init_class
        responses.add(responses.POST, "http://api/job/1/batch", body=b"", status=500)
        with self.assertRaises(Exception):
            list(task._upload_batches("1", [{"Id": "1"}]))


@mock.patch("cumulusci.tasks.bulkdata.time.sleep", mock.Mock())
class TestLoadDataWithSFIds(unittest.TestCase):
    mapping_file = "mapping_v1.yml"

    @responses.activate
    def test_run(self):
        api = mock.Mock()
        api.endpoint = "http://api"
        api.headers.return_value = {}
        api.create_insert_job.side_effect = ["1", "3"]
        api.post_batch.side_effect = ["2", "4"]
        api.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        responses.add(
            method="GET",
            url="http://api/job/1/batch",
            body=BULK_BATCH_RESPONSE.format("Completed"),
            status=200,
        )
        responses.add(
            method="GET",
            url="http://api/job/3/batch",
            body=BULK_BATCH_RESPONSE.format("Completed"),
            status=200,
        )
        responses.add(
            method="GET",
            url="http://api/job/1/batch/2/result",
            body=b"Id,Success,Created,Errors\n1,true,true,",
            status=200,
        )
        responses.add(
            method="GET",
            url="https://example.com/services/data/vNone/query/?q=SELECT+Id+FROM+RecordType+WHERE+SObjectType%3D%27Account%27AND+DeveloperName+%3D+%27HH_Account%27+LIMIT+1",
            body=json.dumps({"records": [{"Id": "1"}]}),
            status=200,
        )
        responses.add(
            method="GET",
            url="http://api/job/3/batch/4/result",
            body=b"Id,Success,Created,Errors\n1,true,true,\n2,true,true,Error",
            status=200,
        )

        base_path = os.path.dirname(__file__)
        db_path = os.path.join(base_path, "testdata.db")
        mapping_path = os.path.join(base_path, self.mapping_file)
        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "testdata.db")
            shutil.copyfile(db_path, tmp_db_path)

            task = _make_task(
                bulkdata.LoadData,
                {
                    "options": {
                        "database_url": "sqlite:///{}".format(tmp_db_path),
                        "mapping": mapping_path,
                    }
                },
            )

            def _init_class():
                task.bulk = api

            task._init_class = _init_class
            task()
            task.session.close()

        households_batch_file = api.post_batch.call_args_list[0][0][1]
        self.assertEqual(
            b"Name,RecordTypeId\r\nTestHousehold,1\r\n", households_batch_file.read()
        )
        contacts_batch_file = api.post_batch.call_args_list[1][0][1]
        self.assertEqual(
            b"FirstName,LastName,Email,AccountId\r\n"
            b"Test,User,test@example.com,1\r\n"
            b"Error,User,error@example.com,1\r\n",
            contacts_batch_file.read(),
        )

    def test_run_task__start_step(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {
                "options": {
                    "database_url": "sqlite://",
                    "mapping": mapping_path,
                    "start_step": "Insert Contacts",
                }
            },
        )
        task._init_db = mock.Mock()
        task._init_mapping = mock.Mock()
        task.mapping = OrderedDict()
        task.mapping["Insert Households"] = 1
        task.mapping["Insert Contacts"] = 2
        task._load_mapping = mock.Mock(return_value="Completed")
        task()
        task._load_mapping.assert_called_once_with(2)

    def test_get_batches__multiple(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        query = mock.Mock()
        query.yield_per.return_value = [[1, 1], [2, 2]]
        task._query_db = mock.Mock(return_value=query)
        mapping = {"sf_object": "Contact"}
        result = list(task._get_batches(mapping, 1))
        self.assertEqual(2, len(result))

    def test_convert(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        self.assertIsInstance(task._convert(datetime.now()), str)

    def test_reset_id_table__already_exists(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task.mapping = {}
        task._init_db()
        id_table = Table(
            "test_sf_ids", task.metadata, Column("id", Unicode(255), primary_key=True)
        )
        id_table.create()
        task._reset_id_table({"table": "test"})
        new_id_table = task.metadata.tables["test_sf_ids"]
        self.assertFalse(new_id_table is id_table)

    def test_run_task__exception_failure(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {
                "options": {
                    "database_url": "sqlite://",
                    "mapping": mapping_path,
                    "start_step": "Insert Contacts",
                }
            },
        )
        task._init_db = mock.Mock()
        task._load_mapping = mock.Mock(return_value="Failed")
        with self.assertRaises(BulkDataException):
            task()

    @responses.activate
    def test_store_inserted_ids__exception_failure(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        api = mock.Mock()
        api.endpoint = "http://api"
        api.headers.return_value = {}
        task.bulk = api

        responses.add(
            method="GET",
            url="http://api/job/1/batch/2/result",
            body=Exception(),
            status=500,
        )
        task.session = mock.Mock()
        task._reset_id_table = mock.Mock()

        with self.assertRaises(BulkDataException) as ex:
            task._store_inserted_ids({"table": "Account"}, "1", {"2": []})

        self.assertIn("Failed to download results", str(ex.exception))

    @responses.activate
    def test_store_inserted_ids__underlying_exception_failure(self):
        result_data = (
            b"Id,Success,Created,Error\n001111111111111,false,false,DUPLICATES_DETECTED"
        )

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        api = mock.Mock()
        api.endpoint = "http://api"
        api.headers.return_value = {}
        task.bulk = api

        results_url = "{}/job/1/batch/2/result".format(task.bulk.endpoint)
        responses.add(method="GET", url=results_url, body=result_data, status=200)

        task.metadata = mock.Mock()
        task.metadata.tables = {"Account": "test"}

        task.session = mock.Mock()
        task._reset_id_table = mock.Mock(return_value="Account")

        with self.assertRaises(BulkDataException) as ex:
            task._store_inserted_ids({"table": "Account"}, "1", {"2": ["3"]})

        self.assertIn("Error on row", str(ex.exception))

    def test_store_inserted_ids_for_batch__exception_failure(self):
        result_data = io.BytesIO(
            b"Id,Success,Created,Error\n001111111111111,false,false,DUPLICATES_DETECTED"
        )

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        task.metadata = mock.Mock()
        task.metadata.tables = {"table": "test"}

        with self.assertRaises(BulkDataException) as ex:
            task._store_inserted_ids_for_batch(
                result_data, ["001111111111111"], "table", mock.Mock()
            )

        self.assertIn("Error on row", str(ex.exception))

    def test_store_inserted_ids_for_batch__respects_silent_error_flag(self):
        result_data = io.BytesIO(
            b"Id,Success,Created,Error\n001111111111111,false,false,DUPLICATES_DETECTED"
        )

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {
                "options": {
                    "ignore_row_errors": True,
                    "database_url": "sqlite://",
                    "mapping": mapping_path,
                }
            },
        )

        task.metadata = mock.Mock()
        task.metadata.tables = {"table": "test"}
        task.session = mock.Mock()

        # This is identical to the test above save the option set to ignore_row_errors
        # We should get no exception.
        task._store_inserted_ids_for_batch(
            result_data, ["001111111111111"], "table", mock.Mock()
        )

    def test_wait_for_job__logs_state_messages(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        task.bulk = mock.Mock()
        task.bulk.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        task._job_state_from_batches = mock.Mock(
            return_value=("Failed", ["Test1", "Test2"])
        )
        task.logger = mock.Mock()

        task._wait_for_job("750000000000000")
        task.logger.error.assert_any_call("Batch failure message: Test1")
        task.logger.error.assert_any_call("Batch failure message: Test2")


@mock.patch("cumulusci.tasks.bulkdata.time.sleep", mock.Mock())
class TestLoadDataWithoutSFIds(unittest.TestCase):
    mapping_file = "mapping_v2.yml"

    @responses.activate
    def test_run(self):
        api = mock.Mock()
        api.endpoint = "http://api"
        api.headers.return_value = {}
        api.create_insert_job.side_effect = ["1", "3"]
        api.post_batch.side_effect = ["2", "4"]
        api.job_status.return_value = {
            "numberBatchesCompleted": 1,
            "numberBatchesTotal": 1,
        }
        responses.add(
            method="GET",
            url="http://api/job/1/batch",
            body=BULK_BATCH_RESPONSE.format("Completed"),
            status=200,
        )
        responses.add(
            method="GET",
            url="http://api/job/3/batch",
            body=BULK_BATCH_RESPONSE.format("Completed"),
            status=200,
        )
        responses.add(
            method="GET",
            url="http://api/job/1/batch/2/result",
            body=b"Id,Success,Created,Errors\n1,true,true,",
            status=200,
        )
        responses.add(
            method="GET",
            url="https://example.com/services/data/vNone/query/?q=SELECT+Id+FROM+RecordType+WHERE+SObjectType%3D%27Account%27AND+DeveloperName+%3D+%27HH_Account%27+LIMIT+1",
            body=json.dumps({"records": [{"Id": "1"}]}),
            status=200,
        )
        responses.add(
            method="GET",
            url="http://api/job/3/batch/4/result",
            body=b"Id,Success,Created,Errors\n1,true,true,\n2,true,true,",
            status=200,
        )

        base_path = os.path.dirname(__file__)
        db_path = os.path.join(base_path, "testdata.db")
        mapping_path = os.path.join(base_path, self.mapping_file)
        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "testdata.db")
            shutil.copyfile(db_path, tmp_db_path)

            task = _make_task(
                bulkdata.LoadData,
                {
                    "options": {
                        "database_url": "sqlite:///{}".format(tmp_db_path),
                        "mapping": mapping_path,
                    }
                },
            )

            def _init_class():
                task.bulk = api

            task._init_class = _init_class
            task()
            task.session.close()

        households_batch_file = api.post_batch.call_args_list[0][0][1]
        self.assertEqual(
            b"Name,RecordTypeId\r\nTestHousehold,1\r\n", households_batch_file.read()
        )
        contacts_batch_file = api.post_batch.call_args_list[1][0][1]
        self.assertEqual(
            b"FirstName,LastName,Email,AccountId\r\n"
            b"Test,User,test@example.com,1\r\n"
            b"Error,User,error@example.com,1\r\n",
            contacts_batch_file.read(),
        )


@mock.patch("cumulusci.tasks.bulkdata.time.sleep", mock.Mock())
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

    def test_create_table__already_exists(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        db_path = os.path.join(base_path, "testdata.db")
        task = _make_task(
            bulkdata.ExtractData,
            {
                "options": {
                    "database_url": "sqlite:///{}".format(db_path),
                    "mapping": mapping_path,
                }
            },
        )
        with self.assertRaises(BulkDataException):
            task()


@mock.patch("cumulusci.tasks.bulkdata.time.sleep", mock.Mock())
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
        self.assertEqual("foo", contact.household_id)


class TestMappingGenerator(unittest.TestCase):
    def test_defaults_options(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        self.assertEqual([], t.options["ignore"])
        self.assertEqual("", t.options["namespace_prefix"])

    def test_postfixes_underscores_to_namespace(self):
        t = _make_task(
            bulkdata.GenerateMapping,
            {"options": {"namespace_prefix": "t", "path": "t"}},
        )

        self.assertEqual("t__", t.options["namespace_prefix"])

    def test_splits_ignore_string(self):
        t = _make_task(
            bulkdata.GenerateMapping,
            {"options": {"ignore": "Account, Contact", "path": "t"}},
        )

        self.assertEqual(["Account", "Contact"], t.options["ignore"])

    def test_accepts_ignore_list(self):
        t = _make_task(
            bulkdata.GenerateMapping,
            {"options": {"ignore": ["Account", "Contact"], "path": "t"}},
        )

        self.assertEqual(["Account", "Contact"], t.options["ignore"])

    def test_is_any_custom_api_name(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        self.assertTrue(t._is_any_custom_api_name("Custom__c"))
        self.assertFalse(t._is_any_custom_api_name("Standard"))

    def test_is_our_custom_api_name(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        self.assertTrue(t._is_our_custom_api_name("Custom__c"))
        self.assertFalse(t._is_our_custom_api_name("Standard"))
        self.assertFalse(t._is_our_custom_api_name("t__Custom__c"))
        self.assertFalse(t._is_our_custom_api_name("f__Custom__c"))

        t.options["namespace_prefix"] = "t__"
        self.assertTrue(t._is_our_custom_api_name("Custom__c"))
        self.assertTrue(t._is_our_custom_api_name("t__Custom__c"))
        self.assertFalse(t._is_our_custom_api_name("f__Custom__c"))

    def test_is_core_field(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        self.assertTrue(t._is_core_field("Id"))
        self.assertFalse(t._is_core_field("Custom__c"))

    def test_is_object_mappable(self):
        t = _make_task(
            bulkdata.GenerateMapping, {"options": {"ignore": "Account", "path": "t"}}
        )

        self.assertTrue(
            t._is_object_mappable({"name": "Contact", "customSetting": False})
        )
        self.assertFalse(
            t._is_object_mappable({"name": "Account", "customSetting": False})
        )
        self.assertFalse(
            t._is_object_mappable(
                {"name": "Contact__ChangeEvent", "customSetting": False}
            )
        )
        self.assertFalse(
            t._is_object_mappable({"name": "Custom__c", "customSetting": True})
        )

    def test_is_field_mappable(self):
        t = _make_task(
            bulkdata.GenerateMapping,
            {"options": {"ignore": "Account.ParentId", "path": "t"}},
        )

        t.mapping_objects = ["Account", "Contact"]

        self.assertTrue(
            t._is_field_mappable(
                "Account",
                {"name": "Name", "type": "string", "label": "Name", "createable": True},
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Account",
                {"name": "Name", "type": "base64", "label": "Name", "createable": True},
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Account",
                {
                    "name": "Name",
                    "type": "string",
                    "label": "Name (Deprecated)",
                    "createable": True,
                },
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Account",
                {
                    "name": "ParentId",
                    "type": "reference",
                    "label": "Parent",
                    "createable": True,
                    "referenceTo": ["Account"],
                },
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Account",
                {
                    "name": "Name",
                    "type": "string",
                    "label": "Name",
                    "createable": False,
                },
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Contact",
                {
                    "name": "ReportsToId",
                    "type": "reference",
                    "label": "Reports To",
                    "createable": True,
                    "referenceTo": ["Contact"],
                },
            )
        )
        self.assertFalse(
            t._is_field_mappable(
                "Contact",
                {
                    "name": "OwnerId",
                    "type": "reference",
                    "label": "Owner",
                    "createable": True,
                    "referenceTo": ["User", "Group"],
                },
            )
        )

    def test_has_our_custom_fields(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        self.assertTrue(t._has_our_custom_fields({"fields": [{"name": "Custom__c"}]}))
        self.assertTrue(
            t._has_our_custom_fields(
                {"fields": [{"name": "Custom__c"}, {"name": "Standard"}]}
            )
        )
        self.assertFalse(t._has_our_custom_fields({"fields": [{"name": "Standard"}]}))
        self.assertFalse(t._has_our_custom_fields({"fields": []}))

    def test_is_lookup_to_included_object(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account"]

        self.assertTrue(
            t._is_lookup_to_included_object(
                {"type": "reference", "referenceTo": ["Account"]}
            )
        )
        self.assertFalse(
            t._is_lookup_to_included_object(
                {"type": "reference", "referenceTo": ["Contact"]}
            )
        )
        self.assertFalse(
            t._is_lookup_to_included_object(
                {"type": "reference", "referenceTo": ["Account", "Contact"]}
            )
        )

    def _prepare_describe_mock(self, task, describe_data):
        responses.add(
            method="GET",
            url="{}/services/data/v45.0/sobjects".format(task.org_config.instance_url),
            body=json.dumps(
                {
                    "sobjects": [
                        {"name": s, "customSetting": False} for s in describe_data
                    ]
                }
            ),
            status=200,
        )
        for s in describe_data:
            body = {"name": s, "customSetting": False}
            body.update(describe_data[s])
            responses.add(
                method="GET",
                url="{}/services/data/v45.0/sobjects/{}/describe".format(
                    task.org_config.instance_url, s
                ),
                body=json.dumps(body),
                status=200,
            )

    def _mock_field(self, name, field_type="string", **kwargs):
        field_data = {
            "name": name,
            "type": field_type,
            "createable": True,
            "nillable": True,
            "label": name,
        }
        field_data.update(kwargs)
        return field_data

    @responses.activate
    def test_run_task(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "mapping.yaml"}})
        t.project_config.project__package__api_version = "45.0"
        describe_data = {
            "Account": {
                "fields": [self._mock_field("Id"), self._mock_field("Custom__c")]
            },
            "Child__c": {
                "fields": [
                    self._mock_field("Id"),
                    self._mock_field(
                        "Account__c",
                        field_type="reference",
                        referenceTo=["Account"],
                        relationshipOrder=None,
                    ),
                ]
            },
        }

        self._prepare_describe_mock(t, describe_data)
        with temporary_dir():
            t()

            with open("mapping.yaml", "r") as fh:
                content = ordered_yaml_load(fh)

            self.assertEqual(
                ["Insert Account", "Insert Child__c"], list(content.keys())
            )
            self.assertEqual("Account", t.mapping["Insert Account"]["sf_object"])
            self.assertEqual("account", t.mapping["Insert Account"]["table"])
            self.assertEqual(
                ["Id", "Custom__c"], list(t.mapping["Insert Account"]["fields"].keys())
            )
            self.assertEqual("sf_id", t.mapping["Insert Account"]["fields"]["Id"])
            self.assertEqual(
                "custom__c", t.mapping["Insert Account"]["fields"]["Custom__c"]
            )

            self.assertEqual("Child__c", t.mapping["Insert Child__c"]["sf_object"])
            self.assertEqual("child__c", t.mapping["Insert Child__c"]["table"])
            self.assertEqual(
                ["Id"], list(t.mapping["Insert Child__c"]["fields"].keys())
            )
            self.assertEqual(
                ["Account__c"], list(t.mapping["Insert Child__c"]["lookups"].keys())
            )
            self.assertEqual("sf_id", t.mapping["Insert Child__c"]["fields"]["Id"])
            self.assertEqual(
                "account",
                t.mapping["Insert Child__c"]["lookups"]["Account__c"]["table"],
            )

    @responses.activate
    def test_collect_objects__simple_custom_objects(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})
        t.project_config.project__package__api_version = "45.0"

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "Contact": {"fields": [self._mock_field("Name")]},
            "Custom__c": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
        }

        self._prepare_describe_mock(t, describe_data)
        t._init_task()
        t._collect_objects()

        self.assertEqual(set(["Account", "Custom__c"]), set(t.mapping_objects))

    @responses.activate
    def test_collect_objects__custom_lookup_fields(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})
        t.project_config.project__package__api_version = "45.0"

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "Contact": {"fields": [self._mock_field("Name")]},
            "Custom__c": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field("Custom__c"),
                    self._mock_field(
                        "Lookup__c",
                        field_type="reference",
                        relationshipOrder=None,
                        referenceTo=["Contact"],
                    ),
                ]
            },
        }

        self._prepare_describe_mock(t, describe_data)
        t._init_task()
        t._collect_objects()

        self.assertEqual(
            set(["Account", "Custom__c", "Contact"]), set(t.mapping_objects)
        )

    @responses.activate
    def test_collect_objects__master_detail_fields(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})
        t.project_config.project__package__api_version = "45.0"

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "Opportunity": {"fields": [self._mock_field("Name")]},
            "OpportunityLineItem": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field("Custom__c"),
                    self._mock_field(
                        "OpportunityId",
                        field_type="reference",
                        relationshipOrder=1,
                        referenceTo=["Opportunity"],
                    ),
                ]
            },
        }

        self._prepare_describe_mock(t, describe_data)
        t._init_task()
        t._collect_objects()

        self.assertEqual(
            set(["Account", "OpportunityLineItem", "Opportunity"]),
            set(t.mapping_objects),
        )

    @responses.activate
    def test_collect_objects__duplicate_references(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})
        t.project_config.project__package__api_version = "45.0"

        describe_data = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Custom__c")]
            },
            "Opportunity": {"fields": [self._mock_field("Name")]},
            "OpportunityLineItem": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field("Custom__c"),
                    self._mock_field(
                        "OpportunityId",
                        field_type="reference",
                        relationshipOrder=1,
                        referenceTo=["Opportunity"],
                    ),
                    self._mock_field(
                        "CustomLookup__c",
                        field_type="reference",
                        relationshipOrder=None,
                        referenceTo=["Opportunity"],
                    ),
                ]
            },
        }

        self._prepare_describe_mock(t, describe_data)
        t._init_task()
        t._collect_objects()

        self.assertEqual(
            set(["Account", "OpportunityLineItem", "Opportunity"]),
            set(t.mapping_objects),
        )

    def test_build_schema(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Opportunity", "Child__c"]
        stage_name = self._mock_field("StageName")
        stage_name["nillable"] = False
        t.describes = {
            "Account": {
                "fields": [self._mock_field("Name"), self._mock_field("Industry")]
            },
            "Opportunity": {"fields": [self._mock_field("Name"), stage_name]},
            "Child__c": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field("Test__c"),
                    self._mock_field("Attachment__c", field_type="base64"),
                ]
            },
        }

        t._build_schema()
        self.assertEqual(
            {
                "Account": {"Name": self._mock_field("Name")},
                "Opportunity": {
                    "Name": self._mock_field("Name"),
                    "StageName": stage_name,
                },
                "Child__c": {
                    "Name": self._mock_field("Name"),
                    "Test__c": self._mock_field("Test__c"),
                },
            },
            t.schema,
        )

    def test_build_schema__tracks_references(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Opportunity"]
        t.describes = {
            "Account": {"fields": [self._mock_field("Name")]},
            "Opportunity": {
                "fields": [
                    self._mock_field("Name"),
                    self._mock_field(
                        "AccountId",
                        field_type="reference",
                        referenceTo=["Account"],
                        relationshipOrder=1,
                    ),
                ]
            },
        }

        t._build_schema()
        self.assertEqual({"Opportunity": {"Account": set(["AccountId"])}}, t.refs)

    def test_build_mapping(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})
        t.schema = {
            "Account": {"Id": self._mock_field("Id"), "Name": self._mock_field("Name")},
            "Child__c": {
                "Id": self._mock_field("Id"),
                "Name": self._mock_field("Name"),
                "Account__c": self._mock_field(
                    "Account__c", field_type="reference", referenceTo=["Account"]
                ),
            },
        }
        t.refs = {"Child__c": {"Account": set(["Account__c"])}}

        t._build_mapping()
        self.assertEqual(["Insert Account", "Insert Child__c"], list(t.mapping.keys()))
        self.assertEqual("Account", t.mapping["Insert Account"]["sf_object"])
        self.assertEqual("account", t.mapping["Insert Account"]["table"])
        self.assertEqual(
            ["Id", "Name"], list(t.mapping["Insert Account"]["fields"].keys())
        )
        self.assertEqual("sf_id", t.mapping["Insert Account"]["fields"]["Id"])
        self.assertEqual("name", t.mapping["Insert Account"]["fields"]["Name"])

        self.assertEqual("Child__c", t.mapping["Insert Child__c"]["sf_object"])
        self.assertEqual("child__c", t.mapping["Insert Child__c"]["table"])
        self.assertEqual(
            ["Id", "Name"], list(t.mapping["Insert Child__c"]["fields"].keys())
        )
        self.assertEqual(
            ["Account__c"], list(t.mapping["Insert Child__c"]["lookups"].keys())
        )
        self.assertEqual("sf_id", t.mapping["Insert Child__c"]["fields"]["Id"])
        self.assertEqual("name", t.mapping["Insert Child__c"]["fields"]["Name"])
        self.assertEqual(
            "account", t.mapping["Insert Child__c"]["lookups"]["Account__c"]["table"]
        )

    def test_build_mapping__warns_polymorphic_lookups(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        t.mapping_objects = ["Account", "Contact", "Custom__c"]
        t.schema = {
            "Account": {"Name": self._mock_field("Name")},
            "Contact": {"Name": self._mock_field("Name")},
            "Custom__c": {
                "Name": self._mock_field("Name"),
                "PolyLookup__c": self._mock_field(
                    "PolyLookup__c",
                    field_type="reference",
                    referenceTo=["Account", "Contact"],
                ),
            },
        }
        t.refs = {
            "Custom__c": {
                "Account": set(["PolyLookup__c"]),
                "Contact": set(["PolyLookup__c"]),
            }
        }
        t.logger = mock.Mock()

        t._build_mapping()
        t.logger.warning.assert_called_once_with(
            "Field Custom__c.PolyLookup__c is a polymorphic lookup, which is not supported"
        )

    def test_split_dependencies__no_cycles(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        stack = t._split_dependencies(
            set(["Account", "Contact", "Opportunity", "Custom__c"]),
            {
                "Contact": {"Account": set(["AccountId"])},
                "Opportunity": {
                    "Account": set(["AccountId"]),
                    "Contact": set(["Primary_Contact__c"]),
                },
                "Custom__c": {
                    "Account": set(["Account__c"]),
                    "Contact": set(["Contact__c"]),
                    "Opportunity": set(["Opp__c"]),
                },
            },
        )

        self.assertEqual(["Account", "Contact", "Opportunity", "Custom__c"], stack)

    def test_split_dependencies__with_cycles(self):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        with self.assertRaises(BulkDataException):
            t._split_dependencies(
                set(["Account", "Contact", "Opportunity", "Custom__c"]),
                {
                    "Account": {"Contact": set(["Primary_Contact__c"])},
                    "Contact": {"Account": set(["AccountId"])},
                    "Opportunity": {
                        "Account": set(["AccountId"]),
                        "Contact": set(["Primary_Contact__c"]),
                    },
                },
            )
