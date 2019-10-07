import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import Integer
from sqlalchemy import Unicode

from cumulusci.core.utils import ordered_yaml_load
from cumulusci.utils import temporary_dir

from cumulusci.tasks.bulkdata.utils import create_table


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
            content = ordered_yaml_load(fh)
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
            content = ordered_yaml_load(fh)
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
