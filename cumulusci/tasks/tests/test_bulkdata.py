from datetime import datetime
import io
import json
import os
import shutil
import unittest

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
        result = obj.process_result_value(1000, None)
        self.assertEqual(datetime(1970, 1, 1, 0, 0, 1), result)

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
        {"instance_url": "example.com", "access_token": "abc123"}, "test"
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
        delete_batch = "4"
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
        task.bulk = api

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
            "InProgress",
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>InProgress</state></batch>"
                "  <batch><state>Failed</state></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )
        self.assertEqual(
            "Failed",
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>Failed</state></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )
        self.assertEqual(
            "Completed",
            task._parse_job_state(
                '<root xmlns="http://ns">'
                "  <batch><state>Completed</state></batch>"
                "  <batch><state>Completed</state></batch>"
                "</root>"
            ),
        )
        self.assertEqual(
            "Aborted",
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
        task.bulk = api
        responses.add(responses.POST, "http://api/job/1/batch", body=b"", status=500)
        with self.assertRaises(Exception):
            list(task._upload_batches("1", [{"Id": "1"}]))


@mock.patch("cumulusci.tasks.bulkdata.time.sleep", mock.Mock())
class TestLoadData(unittest.TestCase):
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
            body=b"Id,Success,Created,Errors\n1,true,true,\n2,false,false,Error",
            status=200,
        )

        base_path = os.path.dirname(__file__)
        db_path = os.path.join(base_path, "testdata.db")
        mapping_path = os.path.join(base_path, "mapping.yml")
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
            task.bulk = api
            task()
            task.session.close()

        households_batch_file = api.post_batch.call_args_list[0][0][1]
        self.assertEqual(
            b"Name,RecordTypeId\r\nHousehold,1\r\n", households_batch_file.read()
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
        mapping_path = os.path.join(base_path, "mapping.yml")
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
        task._load_mapping = mock.Mock()
        task()
        task._load_mapping.assert_called_once()

    def test_get_batches__multiple(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "mapping.yml")
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
        mapping_path = os.path.join(base_path, "mapping.yml")
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        self.assertIsInstance(task._convert(datetime.now()), str)

    def test_reset_id_table__already_exists(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "mapping.yml")
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


HOUSEHOLD_QUERY_RESULT = b'"Id"\n1'
CONTACT_QUERY_RESULT = b'"Id",AccountId\n2,1'


@mock.patch("cumulusci.tasks.bulkdata.time.sleep", mock.Mock())
class TestQueryData(unittest.TestCase):
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
            body=HOUSEHOLD_QUERY_RESULT,
        )
        responses.add(
            responses.GET,
            "http://api/job/2/batch/4/result/6",
            body=CONTACT_QUERY_RESULT,
        )

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "mapping.yml")

        task = _make_task(
            bulkdata.QueryData,
            {
                "options": {
                    "database_url": "sqlite://",  # in memory
                    "mapping": mapping_path,
                }
            },
        )
        task.bulk = api
        task()

        contact = task.session.query(task.models["contacts"]).one()
        self.assertEqual("2", contact.sf_id)
        self.assertEqual("1", contact.household_id)

    def test_sql_bulk_insert_from_csv__postgres(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "mapping.yml")
        task = _make_task(
            bulkdata.QueryData,
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
        mapping_path = os.path.join(base_path, "mapping.yml")
        task = _make_task(
            bulkdata.QueryData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._sql_bulk_insert_from_csv = mock.Mock()
        result_file = io.BytesIO(b"Records not found for this query")
        task._import_results({}, result_file, None)
        task._sql_bulk_insert_from_csv.assert_not_called()

    def test_import_results__no_columns(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "mapping.yml")
        task = _make_task(
            bulkdata.QueryData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task._sql_bulk_insert_from_csv = mock.Mock()
        result_file = io.BytesIO(b"")
        task._import_results({"fields": {}, "lookups": {}}, result_file, None)
        task._sql_bulk_insert_from_csv.assert_not_called()

    def test_create_table__already_exists(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "mapping.yml")
        task = _make_task(
            bulkdata.QueryData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task.models = {"test": mock.Mock()}
        with self.assertRaises(BulkDataException):
            task._create_table({"table": "test"})
