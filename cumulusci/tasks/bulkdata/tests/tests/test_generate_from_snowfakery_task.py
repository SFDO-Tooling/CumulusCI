import unittest
from unittest import mock
from pathlib import Path
from tempfile import NamedTemporaryFile

from cumulusci.tasks.bulkdata.tests.test_bulkdata import _make_task, TaskOptionsError
from cumulusci.tasks.bulkdata import GenerateAndLoadData

import yaml
import pytest
from sqlalchemy import create_engine

snowfakery = pytest.importorskip("snowfakery")

if snowfakery:
    sample_yaml = (
        Path(snowfakery.__file__).parent / "../tests/gen_npsp_standard_objects.yml"
    )
    from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateFromYaml

vanilla_mapping_file = Path(__file__).parent / "../../tests/mapping_vanilla_sf.yml"


def assertRowsCreated(database_url):
    engine = create_engine(database_url)
    connection = engine.connect()
    accounts = connection.execute(f"select * from Account")
    accounts = list(accounts)
    assert accounts and accounts[0] and accounts[0][1]


class FakeLoadData:
    called = False

    def __call__(self, *args, task_config, **kwargs):
        self.called = True
        database_url = task_config.options["database_url"]
        assertRowsCreated(database_url)

        return lambda: ...


class TestGenerateFromDataTask(unittest.TestCase):
    def test_no_options(self):
        with self.assertRaises(Exception):
            _make_task(GenerateFromYaml, {})

    def test_simple(self):
        with NamedTemporaryFile() as t:
            database_url = f"sqlite:///{t.name}"
            task = _make_task(
                GenerateFromYaml,
                {
                    "options": {
                        "generator_yaml": sample_yaml,
                        "num_records": 1,
                        "database_url": database_url,
                    }
                },
            )
            task()
            assertRowsCreated(database_url)

    def test_inaccessible_generator_yaml(self):
        with self.assertRaises(TaskOptionsError):
            task = _make_task(
                GenerateFromYaml,
                {
                    "options": {
                        "generator_yaml": sample_yaml / "junk",
                        "num_records": 10,
                    }
                },
            )
            task()

    def test_vars(self):
        with NamedTemporaryFile() as t:
            database_url = f"sqlite:///{t.name}"
            with self.assertWarns(UserWarning):
                task = _make_task(
                    GenerateFromYaml,
                    {
                        "options": {
                            "generator_yaml": sample_yaml,
                            "vars": "xyzzy:foo",
                            "database_url": database_url,
                        }
                    },
                )
                task()
                assertRowsCreated(database_url)

    def test_generate_mapping_file(self):
        with NamedTemporaryFile() as temp_mapping:
            with NamedTemporaryFile() as temp_db:
                database_url = f"sqlite:///{temp_db.name}"
                task = _make_task(
                    GenerateFromYaml,
                    {
                        "options": {
                            "generator_yaml": sample_yaml,
                            "database_url": database_url,
                            "generate_mapping_file": temp_mapping.name,
                        }
                    },
                )
                task()
            mapping = yaml.safe_load(open(temp_mapping.name))
            assert mapping["Insert Account"]["fields"]

    def test_use_mapping_file(self):
        assert vanilla_mapping_file.exists()
        with NamedTemporaryFile() as temp_db:
            database_url = f"sqlite:///{temp_db.name}"
            task = _make_task(
                GenerateFromYaml,
                {
                    "options": {
                        "generator_yaml": sample_yaml,
                        "database_url": database_url,
                        "mapping": vanilla_mapping_file,
                    }
                },
            )
            task()
            assertRowsCreated(database_url)

    def test_generate_and_load_from_snowfakery(self):
        f = FakeLoadData()
        with mock.patch("cumulusci.tasks.bulkdata.load.LoadData.__new__", f):
            task = _make_task(
                GenerateAndLoadData,
                {
                    "options": {
                        "generator_yaml": sample_yaml,
                        "data_generation_task": "cumulusci.tasks.bulkdata.generate_from_yaml.GenerateFromYaml",
                    }
                },
            )
            task()
            assert f.called
