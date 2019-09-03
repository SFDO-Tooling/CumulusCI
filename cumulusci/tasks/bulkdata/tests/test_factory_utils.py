import unittest
import os

from cumulusci.utils import temporary_dir

from cumulusci.tasks.bulkdata.tests.test_bulkdata import _make_task
from cumulusci.tasks.bulkdata.tests.dummy_data_factory import GenerateDummyData


class TestFactoryUtils(unittest.TestCase):
    def test_factory(self):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_v2.yml")

        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "temp.db")
            dburl = "sqlite:///" + tmp_db_path
            task = _make_task(
                GenerateDummyData,
                {
                    "options": {
                        "num_records": 10,
                        "mapping": mapping_file,
                        "database_url": dburl,
                    }
                },
            )
            task()
