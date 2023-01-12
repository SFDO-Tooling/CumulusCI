import os
from unittest import mock

from sqlalchemy import Unicode

from cumulusci.tasks.bulkdata.base_generate_data_task import BaseGenerateDataTask
from cumulusci.tasks.bulkdata.tests.utils import _make_task
from cumulusci.utils import temporary_dir

NUM_RECORDS = 20


class DummyBaseBatchDataTask(BaseGenerateDataTask):
    """Doesn't actually generate data but validates that we could if we wanted to."""

    def generate_data(self, session, engine, base, num_records, current_batch_num):
        assert os.path.exists(self.options["database_url"].split("///")[1])
        assert session
        assert engine
        assert base.classes["households"]
        assert base.classes["contacts"]
        t = base.classes["contacts"]
        assert isinstance(t.email.type, Unicode)

        assert num_records == NUM_RECORDS
        DummyBaseBatchDataTask.was_called = True


class TestBaseBatchDataTask:
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
            task()
            assert DummyBaseBatchDataTask.was_called

    def test_default_database(self):
        mapping_file = os.path.join(os.path.dirname(__file__), "mapping_v2.yml")
        with mock.patch(
            "cumulusci.tasks.bulkdata.base_generate_data_task.BaseGenerateDataTask._generate_data"
        ) as gen_data:
            task = _make_task(
                DummyBaseBatchDataTask,
                {"options": {"num_records": NUM_RECORDS, "mapping": mapping_file}},
            )
            task()
            gen_data.assert_called_once_with(
                "sqlite:///generated_data.db", mock.ANY, 20, 0
            )
