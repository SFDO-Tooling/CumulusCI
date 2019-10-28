import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Integer
from sqlalchemy import Unicode
import yaml

from cumulusci.utils import temporary_dir

from cumulusci.tasks.bulkdata.utils import create_table, generate_batches


def create_db_file(filename):
    """Create a SQLite file from a filename"""
    db_url = "sqlite:///%s" % filename
    engine = create_engine(db_url)
    metadata = MetaData()
    metadata.bind = engine
    return engine, metadata


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
