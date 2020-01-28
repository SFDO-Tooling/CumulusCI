import os
import responses
import unittest
import yaml

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Integer
from sqlalchemy import types
from sqlalchemy import Unicode
from unittest import mock

from cumulusci.tasks import bulkdata
from cumulusci.tasks.bulkdata.utils import create_table, generate_batches
from cumulusci.utils import temporary_dir


def create_db_file(filename):
    """Create a SQLite file from a filename"""
    db_url = "sqlite:///%s" % filename
    engine = create_engine(db_url)
    metadata = MetaData()
    metadata.bind = engine
    return engine, metadata


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
        util = bulkdata.utils.SqlAlchemyMixin()
        util.models = {}
        util.metadata = mock.Mock()

        util._create_record_type_table("Account_rt_mapping")

        self.assertIn("Account_rt_mapping", util.models)

    @responses.activate
    def test_extract_record_types(self):
        util = bulkdata.utils.SqlAlchemyMixin()
        util._sql_bulk_insert_from_records = mock.Mock()
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
        util._sql_bulk_insert_from_records.assert_called_once()
        call = util._sql_bulk_insert_from_records.call_args_list[0][0]
        assert call[0] == conn
        assert call[1] == "test_table"
        assert call[2] == ["record_type_id", "developer_name"]
        assert list(call[3]) == [["012000000000000", "Organization"]]


class TestCreateTable(unittest.TestCase):
    def test_create_table_legacy_oid_mapping(self):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_v1.yml")
        with open(mapping_file, "r") as fh:
            content = yaml.safe_load(fh)
            account_mapping = content["Insert Contacts"]

        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "temp.db")

            engine, metadata = create_db_file(tmp_db_path)
            t = create_table(account_mapping, metadata)
            assert t.name == "contacts"
            assert isinstance(t.columns["sf_id"].type, Unicode)
            assert isinstance(t.columns["first_name"].type, Unicode)
            assert isinstance(t.columns["last_name"].type, Unicode)
            assert isinstance(t.columns["email"].type, Unicode)

    def test_create_table_modern_id_mapping(self):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_v2.yml")
        with open(mapping_file, "r") as fh:
            content = yaml.safe_load(fh)
            account_mapping = content["Insert Contacts"]

        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "temp.db")

            engine, metadata = create_db_file(tmp_db_path)
            t = create_table(account_mapping, metadata)
            assert t.name == "contacts"
            assert isinstance(t.columns["id"].type, Integer)
            assert isinstance(t.columns["first_name"].type, Unicode)
            assert isinstance(t.columns["last_name"].type, Unicode)
            assert isinstance(t.columns["email"].type, Unicode)


class TestBatching(unittest.TestCase):
    def test_batching_no_remainder(self):
        batches = list(generate_batches(num_records=20, batch_size=10))
        assert batches == [(10, 0), (10, 1)]

        batches = list(generate_batches(num_records=20, batch_size=5))
        assert batches == [(5, 0), (5, 1), (5, 2), (5, 3)]

        batches = list(generate_batches(num_records=3, batch_size=1))
        assert batches == [(1, 0), (1, 1), (1, 2)]

        batches = list(generate_batches(num_records=3, batch_size=3))
        assert batches == [(3, 0)]

    def test_batching_with_remainder(self):
        batches = list(generate_batches(num_records=20, batch_size=7))
        assert batches == [(7, 0), (7, 1), (6, 2)]
