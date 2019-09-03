import os
import unittest

from sqlalchemy import Unicode

from cumulusci.tasks.bulkdata.base_generate_data_task import BaseGenerateDataTask
from cumulusci.tasks.bulkdata.tests.test_bulkdata import _make_task
from cumulusci.utils import temporary_dir


NUM_RECORDS = 20


class DummyBaseBatchDataTask(BaseGenerateDataTask):
    """Doesn't actually generate data but validates that we could if we wanted to."""

    def generate_data(self, session, engine, base, num_records):
        assert os.path.exists(self._testfilename)
        assert session
        assert engine
        assert base.classes["households"]
        assert base.classes["contacts"]
        t = base.classes["contacts"]
        assert isinstance(t.email.type, Unicode)

        assert num_records == NUM_RECORDS


class TestBaseBatchDataTask(unittest.TestCase):
    def test_BaseBatchDataTask(self):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_v2.yml")
        with temporary_dir() as d:
            tmp_db_path = os.path.join(d, "temp.db")
            dburl = "sqlite:///" + tmp_db_path

            task = _make_task(
                DummyBaseBatchDataTask,
                {
                    "options": {
                        "num_records": NUM_RECORDS,
                        "mapping": mapping_file,
                        "database_url": dburl,
                    }
                },
            )
            task._testfilename = tmp_db_path
            task()
