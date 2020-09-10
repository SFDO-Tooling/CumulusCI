from datetime import datetime
import os
import unittest
from unittest import mock

import responses
from sqlalchemy import create_engine, MetaData, Integer, types, Unicode, Column, Table
from sqlalchemy.orm import create_session, mapper

from cumulusci.tasks import bulkdata
from cumulusci.utils import temporary_dir
from cumulusci.tasks.bulkdata.utils import create_table, generate_batches
from cumulusci.tasks.bulkdata.mapping_parser import parse_from_yaml


def create_db_file(filename):
    """Create a SQLite file from a filename"""
    db_url = "sqlite:///%s" % filename
    engine = create_engine(db_url)
    metadata = MetaData()
    metadata.bind = engine
    return engine, metadata


def create_db_memory():
    """Create a SQLite database in memory"""
    db_url = "sqlite:///"
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


class TestSqlAlchemyMixin(unittest.TestCase):
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
            "totalSize": 1,
            "records": [{"Id": "012000000000000", "DeveloperName": "Organization"}],
        }
        util.logger = mock.Mock()

        conn = mock.Mock()
        util._extract_record_types("Account", "test_table", conn)

        util.sf.query.assert_called_once_with(
            "SELECT Id, DeveloperName FROM RecordType WHERE SObjectType='Account'"
        )
        util._sql_bulk_insert_from_records.assert_called_once()
        call = util._sql_bulk_insert_from_records.call_args_list[0][1]
        assert call["connection"] == conn
        assert call["table"] == "test_table"
        assert call["columns"] == ["record_type_id", "developer_name"]
        assert list(call["record_iterable"]) == [["012000000000000", "Organization"]]

    def test_sql_bulk_insert_from_records__sqlite(self):
        engine, metadata = create_db_memory()
        fields = [
            Column("id", Integer(), primary_key=True, autoincrement=True),
            Column("sf_id", Unicode(24)),
        ]
        id_t = Table("TestTable", metadata, *fields)
        id_t.create()
        model = type("TestModel", (object,), {})
        mapper(model, id_t)

        util = bulkdata.utils.SqlAlchemyMixin()
        util.metadata = metadata
        session = create_session(bind=engine, autocommit=False)
        util.session = session
        connection = session.connection()

        util._sql_bulk_insert_from_records(
            connection=connection,
            table="TestTable",
            columns=("id", "sf_id"),
            record_iterable=([f"{x}", f"00100000000000{x}"] for x in range(10)),
        )

        assert session.query(model).count() == 10


class TestCreateTable(unittest.TestCase):
    def test_create_table_legacy_oid_mapping(self):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_v1.yml")

        content = parse_from_yaml(mapping_file)
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
        content = parse_from_yaml(mapping_file)
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
