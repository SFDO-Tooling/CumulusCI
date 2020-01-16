from collections import OrderedDict
from datetime import datetime
import io
import json
import os
import shutil
import unicodecsv
import unittest

from sqlalchemy import Column
from sqlalchemy import Table
from sqlalchemy import types
from sqlalchemy import Unicode
from unittest import mock
import responses
import yaml

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import BulkDataException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks import bulkdata
from cumulusci.tests.util import DummyOrgConfig
from cumulusci.utils import temporary_dir


class TestEpochType(unittest.TestCase):
    def test_process_bind_param(self):
        obj = bulkdata.utils.EpochType()
        dt = datetime(1970, 1, 1, 0, 0, 1)
        result = obj.process_bind_param(dt, None)
        self.assertEqual(1000, result)

    def test_process_result_value(self):
        obj = bulkdata.utils.EpochType()

        # Non-None value
        result = obj.process_result_value(1000, None)
        self.assertEqual(datetime(1970, 1, 1, 0, 0, 1), result)

        # None value
        result = obj.process_result_value(None, None)
        self.assertEqual(None, result)

    def test_setup_epoch(self):
        column_info = {"type": types.DateTime()}
        bulkdata.utils.setup_epoch(mock.Mock(), mock.Mock(), column_info)
        self.assertIsInstance(column_info["type"], bulkdata.utils.EpochType)


class TestRecordTypeUtils(unittest.TestCase):
    @mock.patch("cumulusci.tasks.bulkdata.utils.Table")
    @mock.patch("cumulusci.tasks.bulkdata.utils.mapper")
    def test_create_record_type_table(self, mapper, table):
        util = bulkdata.utils.BulkJobTaskMixin()
        util.models = {}
        util.metadata = mock.Mock()

        util._create_record_type_table("Account_rt_mapping")

        self.assertIn("Account_rt_mapping", util.models)

    @responses.activate
    def test_extract_record_types(self):
        util = bulkdata.utils.BulkJobTaskMixin()
        util._sql_bulk_insert_from_csv = mock.Mock()
        util.sf = mock.Mock()
        util.sf.query.return_value = {
            "records": [{"Id": "012000000000000", "DeveloperName": "Organization"}]
        }
        util.logger = mock.Mock()

        conn = mock.Mock()
        util._extract_record_types("Account", "test_table", conn)

        util.sf.query.assert_called_once_with(
            "SELECT Id, DeveloperName FROM RecordType WHERE SObjectType='Account'"
        )
        util._sql_bulk_insert_from_csv.assert_called_once()
        call = util._sql_bulk_insert_from_csv.call_args_list[0][0]
        assert call[0] == conn
        assert call[1] == "test_table"
        assert call[2] == ["record_type_id", "developer_name"]
        assert call[3].read().strip() == b"012000000000000,Organization"


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
                        "database_url": f"sqlite:///{tmp_db_path}",
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
        task.mapping = {}
        task.mapping["Insert Households"] = {"one": 1}
        task.mapping["Insert Contacts"] = {"two": 2}
        task.after_steps = {}
        task._load_mapping = mock.Mock(return_value="Completed")
        task()
        task._load_mapping.assert_called_once_with({"two": 2, "action": "insert"})

    def test_run_task__after_steps(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
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
        task._load_mapping = mock.Mock(return_value="Completed")
        task()
        task._load_mapping.assert_has_calls(
            [mock.call(1), mock.call(4), mock.call(5), mock.call(2), mock.call(3)]
        )

    def test_create_job__update(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task.bulk = mock.Mock()
        task._get_batches = mock.Mock(return_value=[])
        mapping = {"action": "update", "sf_object": "Account"}

        task._create_job(mapping)

        task.bulk.create_update_job.assert_called_once_with(
            "Account", contentType="CSV", concurrency="Parallel"
        )

    def test_create_job__serial(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        task.bulk = mock.Mock()
        task._get_batches = mock.Mock(return_value=[])
        mapping = {"action": "update", "sf_object": "Account", "bulk_mode": "Serial"}

        task._create_job(mapping)

        task.bulk.create_update_job.assert_called_once_with(
            "Account", contentType="CSV", concurrency="Serial"
        )

    def test_create_job__serial_task_level(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {
                "options": {
                    "database_url": "sqlite://",
                    "mapping": mapping_path,
                    "bulk_mode": "Serial",
                }
            },
        )
        task.bulk = mock.Mock()
        task._get_batches = mock.Mock(return_value=[])
        mapping = {"action": "update", "sf_object": "Account"}

        task._create_job(mapping)

        task.bulk.create_update_job.assert_called_once_with(
            "Account", contentType="CSV", concurrency="Serial"
        )

    def test_run_task__after_steps_failure(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
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
        task._load_mapping = mock.Mock(side_effect=["Completed", "Failed"])
        with self.assertRaises(BulkDataException):
            task()

    @responses.activate
    def test_run__sql(self):
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
        sql_path = os.path.join(base_path, "testdata.sql")
        mapping_path = os.path.join(base_path, self.mapping_file)

        task = _make_task(
            bulkdata.LoadData,
            {"options": {"sql_path": sql_path, "mapping": mapping_path}},
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

    def test_init_options__missing_input(self):
        with self.assertRaises(TaskOptionsError):
            _make_task(bulkdata.LoadData, {"options": {}})

    def test_init_options__invalid_bulk_mode(self):
        with self.assertRaises(TaskOptionsError) as e:
            _make_task(
                bulkdata.LoadData,
                {"options": {"bulk_mode": "nonsense", "database_url": "foo://bar"}},
            )
        assert "Serial" in str(e.exception), e

    def test_init_options__case_insensitive(self):
        task = _make_task(
            bulkdata.LoadData,
            {
                "options": {
                    "bulk_mode": "SERIAL",
                    "database_url": "foo://bar",
                    "mapping": "foo.yml",
                }
            },
        )
        assert task.bulk_mode == "Serial"

    def test_expand_mapping_creates_after_steps(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "mapping_after.yml")
        task = _make_task(
            bulkdata.LoadData,
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
        lookups["Id"] = {"table": "accounts", "key_field": "sf_id"}
        lookups["Primary_Contact__c"] = {"table": "contacts"}
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
        lookups["Id"] = {"table": "contacts", "key_field": "sf_id"}
        lookups["ReportsToId"] = {"table": "contacts"}
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
        lookups["Id"] = {"table": "accounts", "key_field": "sf_id"}
        lookups["ParentId"] = {"table": "accounts"}
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
        mapping = {"sf_object": "Contact", "action": "insert"}
        result = list(task._get_batches(mapping, 1))
        self.assertEqual(2, len(result))

    def test_get_batches__columns(self):
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "test.yml"}},
        )
        task.sf = mock.Mock()
        task.sf.query.return_value = {"records": [{"Id": "012000000000000"}]}

        mapping = {
            "sf_object": "Account",
            "action": "insert",
            "fields": {"Id": "sf_id", "Name": "Name"},
            "static": {"Industry": "Technology"},
            "record_type": "Organization",
        }

        writer = mock.Mock()
        batch_ids = mock.Mock()
        batch_file = mock.Mock()

        task._query_db = mock.Mock()
        task._query_db.return_value.yield_per = mock.Mock(
            return_value=[["001000000001", "TestCo"]]
        )
        task._start_batch = mock.Mock(return_value=(batch_file, writer, batch_ids))
        batches = list(task._get_batches(mapping))

        self.assertEqual(1, len(batches))
        self.assertEqual((batch_file, batch_ids), batches[0])

        writer.writerow.assert_has_calls(
            [mock.call(["TestCo", "Technology", "012000000000000"])]
        )
        batch_ids.append.assert_called_once_with("001000000001")

    def test_get_batches__skips_empty_rows(self):
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "test.yml"}},
        )
        task.sf = mock.Mock()

        mapping = {
            "sf_object": "Account",
            "action": "update",
            "fields": {},
            "lookups": {"ParentId": {"table": "accounts", "key_field": "sf_id"}},
        }

        writer = mock.Mock()
        batch_ids = []
        batch_file = mock.Mock()

        task._query_db = mock.Mock()
        task._query_db.return_value.yield_per = mock.Mock(
            return_value=[["001000000001", "001000000002", None]]
        )
        task._start_batch = mock.Mock(return_value=(batch_file, writer, batch_ids))
        batches = list(task._get_batches(mapping))
        self.assertEqual(0, len(batches))

    def test_get_columns(self):
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "test.yml"}},
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
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "test.yml"}},
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

    def test_start_batch(self):
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "test.yml"}},
        )

        batch_file, writer, batch_ids = task._start_batch(["Test"])
        self.assertIsInstance(writer, unicodecsv.writer)

    @mock.patch("cumulusci.tasks.bulkdata.load.aliased")
    def test_query_db__joins_self_lookups(self, aliased):
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "test.yml"}},
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
            "lookups": {"ParentId": {"table": "accounts", "key_field": "sf_id"}},
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
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )
        self.assertIsInstance(task._convert(datetime.now()), str)

    def test_initialize_id_table__already_exists(self):
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
        task._initialize_id_table({"table": "test"}, True)
        new_id_table = task.metadata.tables["test_sf_ids"]
        self.assertFalse(new_id_table is id_table)

    def test_initialize_id_table__already_exists_and_should_not_reset_table(self):
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
        table_name = task._initialize_id_table({"table": "test"}, False)
        assert table_name == "test_sf_ids"
        new_id_table = task.metadata.tables["test_sf_ids"]
        assert new_id_table is id_table

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
    def test_process_job_results__insert_success(self):
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

        result_data = b"Id,Success,Created,Error\n001111111111111,true,true,"

        responses.add(
            method="GET",
            url="http://api/job/1/batch/2/result",
            body=result_data,
            status=200,
        )
        task.session = mock.Mock()
        task._initialize_id_table = mock.Mock()
        task._sql_bulk_insert_from_csv = mock.Mock()

        mapping = {"table": "Account", "action": "insert"}
        task._process_job_results(mapping, "1", {"2": ["001111111111112"]})

        task.session.connection.assert_called_once()
        task._initialize_id_table.assert_called_once_with(mapping, True)
        task._sql_bulk_insert_from_csv.assert_called_once()
        task.session.commit.assert_called_once()

    @responses.activate
    def test_process_job_results__update_success(self):
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

        result_data = b"Id,Success,Created,Error\n001111111111111,true,false,"

        responses.add(
            method="GET",
            url="http://api/job/1/batch/2/result",
            body=result_data,
            status=200,
        )
        task.session = mock.Mock()
        task._initialize_id_table = mock.Mock()
        task._sql_bulk_insert_from_csv = mock.Mock()

        mapping = {"table": "Account", "action": "update"}
        task._process_job_results(mapping, "1", {"2": ["001111111111112"]})

        task.session.connection.assert_not_called()
        task._initialize_id_table.assert_not_called()
        task._sql_bulk_insert_from_csv.assert_not_called()
        task.session.commit.assert_not_called()

    @responses.activate
    def test_process_job_results__exception_failure(self):
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
        task._initialize_id_table = mock.Mock()

        with self.assertRaises(BulkDataException) as ex:
            task._process_job_results(
                {"table": "Account", "action": "insert"}, "1", {"2": []}
            )

        self.assertIn("Failed to download results", str(ex.exception))

    @responses.activate
    def test_process_job_results__underlying_exception_failure(self):
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

        results_url = f"{task.bulk.endpoint}/job/1/batch/2/result"
        responses.add(method="GET", url=results_url, body=result_data, status=200)

        task.metadata = mock.Mock()
        task.metadata.tables = {"Account": "test"}

        task.session = mock.Mock()
        task._initialize_id_table = mock.Mock(return_value="Account")

        with self.assertRaises(BulkDataException) as ex:
            task._process_job_results(
                {"table": "Account", "action": "insert"}, "1", {"2": ["3"]}
            )

        self.assertIn("Error on row", str(ex.exception))

    def test_generate_results_id_map__success(self):
        result_data = io.BytesIO(
            b"Id,Success,Created,Error\n"
            b"001111111111111,true,true,\n"
            b"001111111111112,true,true,"
        )

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        task.metadata = mock.Mock()
        task.metadata.tables = {"table": "test"}

        generator = task._generate_results_id_map(
            result_data, ["001000000000000", "001000000000001"]
        )

        self.assertEqual(
            [
                b"001000000000000,001111111111111\n",
                b"001000000000001,001111111111112\n",
            ],
            list(generator),
        )

    def test_generate_results_id_map__exception_failure(self):
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
            list(task._generate_results_id_map(result_data, ["001111111111111"]))

        self.assertIn("Error on row", str(ex.exception))

    def test_generate_results_id_map__respects_silent_error_flag(self):
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
        list(task._generate_results_id_map(result_data, ["001111111111111"]))

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

    def test_load_mapping__record_type_mapping(self):
        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, self.mapping_file)
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": mapping_path}},
        )

        task.session = mock.Mock()
        task._create_job = mock.Mock(return_value=("test", 1))
        task._wait_for_job = mock.Mock()
        task._process_job_results = mock.Mock()
        task._load_record_types = mock.Mock()

        task._load_mapping({"sf_object": "Account", "fields": {"Name": "Name"}})

        task._load_record_types.assert_not_called()

        task._load_mapping(
            {
                "sf_object": "Account",
                "fields": {"Name": "Name", "RecordTypeId": "RecordTypeId"},
            }
        )
        task._load_record_types.assert_called_once_with(
            ["Account"], task.session.connection.return_value
        )

    def test_query_db__record_type_mapping(self):
        task = _make_task(
            bulkdata.LoadData,
            {"options": {"database_url": "sqlite://", "mapping": "test.yml"}},
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
            bulkdata.LoadData,
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
            bulkdata.LoadData, {"options": {"database_url": "sqlite://", "mapping": ""}}
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
                        "database_url": f"sqlite:///{tmp_db_path}",
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
            url=f"{task.org_config.instance_url}/services/data/v45.0/sobjects",
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
                url=f"{task.org_config.instance_url}/services/data/v45.0/sobjects/{s}/describe",
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
            "Parent": {
                "fields": [self._mock_field("Id"), self._mock_field("Custom__c")]
            },
            "Child__c": {
                "fields": [
                    self._mock_field("Id"),
                    self._mock_field(
                        "Account__c",
                        field_type="reference",
                        referenceTo=["Parent"],
                        relationshipOrder=None,
                    ),
                ]
            },
        }

        self._prepare_describe_mock(t, describe_data)
        with temporary_dir():
            t()

            with open("mapping.yaml", "r") as fh:
                content = yaml.safe_load(fh)

            self.assertEqual(["Insert Parent", "Insert Child__c"], list(content.keys()))
            self.assertEqual("Parent", t.mapping["Insert Parent"]["sf_object"])
            self.assertEqual("Parent", t.mapping["Insert Parent"]["table"])
            self.assertEqual(
                ["Id", "Custom__c"], list(t.mapping["Insert Parent"]["fields"].keys())
            )
            self.assertEqual("sf_id", t.mapping["Insert Parent"]["fields"]["Id"])
            self.assertEqual(
                "Custom__c", t.mapping["Insert Parent"]["fields"]["Custom__c"]
            )

            self.assertEqual("Child__c", t.mapping["Insert Child__c"]["sf_object"])
            self.assertEqual("Child__c", t.mapping["Insert Child__c"]["table"])
            self.assertEqual(
                ["Id"], list(t.mapping["Insert Child__c"]["fields"].keys())
            )
            self.assertEqual(
                ["Account__c"], list(t.mapping["Insert Child__c"]["lookups"].keys())
            )
            self.assertEqual("sf_id", t.mapping["Insert Child__c"]["fields"]["Id"])
            self.assertEqual(
                "Parent", t.mapping["Insert Child__c"]["lookups"]["Account__c"]["table"]
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

    def test_build_schema__includes_recordtypeid(self):
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
                    self._mock_field("RecordTypeId"),
                ],
                "recordTypeInfos": [{"Name": "Master"}, {"Name": "Donation"}],
            },
        }

        t._build_schema()
        self.assertIn("RecordTypeId", t.schema["Opportunity"])
        self.assertNotIn("RecordTypeId", t.schema["Account"])

    @mock.patch("click.prompt")
    def test_build_mapping(self, prompt):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})
        prompt.return_value = "Account"

        t.schema = {
            "Account": {
                "Id": self._mock_field("Id"),
                "Name": self._mock_field("Name"),
                "Dependent__c": self._mock_field(
                    "Dependent__c", field_type="reference", referenceTo=["Child__c"]
                ),
            },
            "Child__c": {
                "Id": self._mock_field("Id"),
                "Name": self._mock_field("Name"),
                "Account__c": self._mock_field(
                    "Account__c", field_type="reference", referenceTo=["Account"]
                ),
                "Self__c": self._mock_field(
                    "Self__c", field_type="reference", referenceTo=["Child__c"]
                ),
            },
        }
        t.refs = {
            "Child__c": {"Account": set(["Account__c"])},
            "Account": {"Child__c": set(["Dependent__c"])},
        }

        t._build_mapping()
        self.assertEqual(["Insert Account", "Insert Child__c"], list(t.mapping.keys()))
        self.assertEqual("Account", t.mapping["Insert Account"]["sf_object"])
        self.assertEqual("Account", t.mapping["Insert Account"]["table"])
        self.assertEqual(
            ["Id", "Name"], list(t.mapping["Insert Account"]["fields"].keys())
        )
        self.assertEqual("sf_id", t.mapping["Insert Account"]["fields"]["Id"])
        self.assertEqual("Name", t.mapping["Insert Account"]["fields"]["Name"])
        self.assertEqual(
            ["Dependent__c"], list(t.mapping["Insert Account"]["lookups"].keys())
        )
        self.assertEqual(
            "Child__c", t.mapping["Insert Account"]["lookups"]["Dependent__c"]["table"]
        )

        self.assertEqual("Child__c", t.mapping["Insert Child__c"]["sf_object"])
        self.assertEqual("Child__c", t.mapping["Insert Child__c"]["table"])
        self.assertEqual(
            ["Id", "Name"], list(t.mapping["Insert Child__c"]["fields"].keys())
        )
        self.assertEqual(
            ["Account__c", "Self__c"],
            list(t.mapping["Insert Child__c"]["lookups"].keys()),
        )
        self.assertEqual("sf_id", t.mapping["Insert Child__c"]["fields"]["Id"])
        self.assertEqual("Name", t.mapping["Insert Child__c"]["fields"]["Name"])
        self.assertEqual(
            "Account", t.mapping["Insert Child__c"]["lookups"]["Account__c"]["table"]
        )
        self.assertEqual(
            "Child__c", t.mapping["Insert Child__c"]["lookups"]["Self__c"]["table"]
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

    @mock.patch("click.prompt")
    def test_split_dependencies__interviews_for_cycles(self, prompt):
        t = _make_task(bulkdata.GenerateMapping, {"options": {"path": "t"}})

        prompt.return_value = "Account"

        self.assertEqual(
            ["Custom__c", "Account", "Contact", "Opportunity"],
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
            ),
        )
