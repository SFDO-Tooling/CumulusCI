import os
from unittest import mock

import responses
from sqlalchemy import Column, Integer, MetaData, Table, Unicode, create_engine
from sqlalchemy.orm import create_session, mapper

from cumulusci.tasks import bulkdata
from cumulusci.tasks.bulkdata.mapping_parser import parse_from_yaml
from cumulusci.tasks.bulkdata.utils import (
    create_table,
    generate_batches,
    sql_bulk_insert_from_records,
)
from cumulusci.utils import temporary_dir


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


class TestSqlAlchemyMixin:
    @mock.patch("cumulusci.tasks.bulkdata.utils.Table")
    @mock.patch("cumulusci.tasks.bulkdata.utils.mapper")
    def test_create_record_type_table(self, mapper, table):
        util = bulkdata.utils.SqlAlchemyMixin()
        util.models = {}
        util.metadata = mock.Mock()

        util._create_record_type_table("Account_rt_mapping")

        assert "Account_rt_mapping" in util.models

    @responses.activate
    def test_extract_record_types(self):
        util = bulkdata.utils.SqlAlchemyMixin()
        util.sf = mock.Mock()
        util.sf.query.return_value = {
            "totalSize": 1,
            "records": [{"Id": "012000000000000", "DeveloperName": "Organization"}],
        }
        util.logger = mock.Mock()
        util.metadata = mock.MagicMock()

        conn = mock.MagicMock()
        with mock.patch(
            "cumulusci.tasks.bulkdata.utils.sql_bulk_insert_from_records"
        ) as sql_bulk_insert_from_records:
            util._extract_record_types("Account", "test_table", conn)

        util.sf.query.assert_called_once_with(
            "SELECT Id, DeveloperName FROM RecordType WHERE SObjectType='Account'"
        )
        sql_bulk_insert_from_records.assert_called_once()
        call = sql_bulk_insert_from_records.call_args_list[0][1]
        assert call["connection"] == conn
        assert call["table"] == util.metadata.tables["test_table"]
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

        session = create_session(bind=engine, autocommit=False)
        connection = session.connection()

        sql_bulk_insert_from_records(
            connection=connection,
            table=id_t,
            columns=("id", "sf_id"),
            record_iterable=([f"{x}", f"00100000000000{x}"] for x in range(10)),
        )

        assert session.query(model).count() == 10


class TestCreateTable:
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


class TestBatching:
    def test_batching_no_remainder(self):
        batches = list(generate_batches(num_records=20, batch_size=10))
        assert batches == [(10, 0, 2), (10, 1, 2)], batches

        batches = list(generate_batches(num_records=20, batch_size=5))
        assert batches == [(5, 0, 4), (5, 1, 4), (5, 2, 4), (5, 3, 4)], batches

        batches = list(generate_batches(num_records=3, batch_size=1))
        assert batches == [(1, 0, 3), (1, 1, 3), (1, 2, 3)], batches

        batches = list(generate_batches(num_records=3, batch_size=3))
        assert batches == [(3, 0, 1)], batches

    def test_batching_with_remainder(self):
        batches = list(generate_batches(num_records=20, batch_size=7))
        assert batches == [(7, 0, 3), (7, 1, 3), (6, 2, 3)], batches
