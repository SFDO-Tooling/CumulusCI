import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import contextmanager

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.tests.utils import _make_task

import yaml
import pytest
from sqlalchemy import create_engine

from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from snowfakery import data_generator_runtime

sample_yaml = Path(__file__).parent / "snowfakery/gen_npsp_standard_objects.yml"
simple_yaml = Path(__file__).parent / "snowfakery/include_parent.yml"
from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml

vanilla_mapping_file = Path(__file__).parent / "../tests/mapping_vanilla_sf.yml"


@contextmanager
def temporary_file_path(filename):
    with TemporaryDirectory() as tmpdirname:
        path = Path(tmpdirname) / filename
        yield path


@contextmanager
def temp_sqlite_database_url():
    with temporary_file_path("test.db") as path:
        yield f"sqlite:///{str(path)}"


class TestGenerateFromDataTask(unittest.TestCase):
    def assertRowsCreated(self, database_url):
        engine = create_engine(database_url)
        connection = engine.connect()
        accounts = connection.execute("select * from Account")
        accounts = list(accounts)
        assert accounts and accounts[0] and accounts[0][1]
        return accounts

    def test_no_options(self):
        with self.assertRaises(Exception):
            _make_task(GenerateDataFromYaml, {})

    def test_simple(self):
        with temp_sqlite_database_url() as database_url:
            task = _make_task(
                GenerateDataFromYaml,
                {
                    "options": {
                        "generator_yaml": sample_yaml,
                        "num_records": 1,
                        "database_url": database_url,
                        "num_records_tablename": "Account",
                    }
                },
            )
            task()
            self.assertRowsCreated(database_url)

    def test_inaccessible_generator_yaml(self):
        with self.assertRaises(TaskOptionsError):
            task = _make_task(
                GenerateDataFromYaml,
                {
                    "options": {
                        "generator_yaml": sample_yaml / "junk",
                        "num_records": 10,
                        "num_records_tablename": "Account",
                    }
                },
            )
            task()

    def test_vars(self):
        with temp_sqlite_database_url() as database_url:
            with self.assertWarns(UserWarning):
                task = _make_task(
                    GenerateDataFromYaml,
                    {
                        "options": {
                            "generator_yaml": sample_yaml,
                            "vars": "xyzzy:foo",
                            "database_url": database_url,
                        }
                    },
                )
                task()
                self.assertRowsCreated(database_url)

    def test_generate_mapping_file(self):
        with temporary_file_path("mapping.yml") as temp_mapping:
            with temp_sqlite_database_url() as database_url:
                task = _make_task(
                    GenerateDataFromYaml,
                    {
                        "options": {
                            "generator_yaml": sample_yaml,
                            "database_url": database_url,
                            "generate_mapping_file": temp_mapping,
                        }
                    },
                )
                task()
            mapping = yaml.safe_load(open(temp_mapping))
            assert mapping["Insert Account"]["fields"]

    def test_use_mapping_file(self):
        assert vanilla_mapping_file.exists()
        with temp_sqlite_database_url() as database_url:
            task = _make_task(
                GenerateDataFromYaml,
                {
                    "options": {
                        "generator_yaml": sample_yaml,
                        "database_url": database_url,
                        "mapping": vanilla_mapping_file,
                    }
                },
            )
            task()
            self.assertRowsCreated(database_url)

    def test_num_records(self):
        with temp_sqlite_database_url() as database_url:
            task = _make_task(
                GenerateDataFromYaml,
                {
                    "options": {
                        "generator_yaml": simple_yaml,
                        "num_records": 11,
                        "database_url": database_url,
                        "num_records_tablename": "Account",
                    }
                },
            )
            task()
            assert len(self.assertRowsCreated(database_url)) == 11

    @mock.patch(
        "cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml.GenerateAndLoadDataFromYaml._dataload"
    )
    def test_simple_generate_and_load(self, _dataload):
        task = _make_task(
            GenerateAndLoadDataFromYaml,
            {
                "options": {
                    "generator_yaml": simple_yaml,
                    "num_records": 11,
                    "num_records_tablename": "Account",
                }
            },
        )
        task()
        assert len(_dataload.mock_calls) == 1

    @mock.patch("cumulusci.tasks.bulkdata.generate_from_yaml.generate")
    def test_exception_handled_cleanly(self, generate):
        generate.side_effect = AssertionError("Foo")
        with pytest.raises(AssertionError) as e:
            task = _make_task(
                GenerateAndLoadDataFromYaml,
                {
                    "options": {
                        "generator_yaml": simple_yaml,
                        "num_records": 11,
                        "num_records_tablename": "Account",
                    }
                },
            )
            task()
            assert "Foo" in str(e.value)
        assert len(generate.mock_calls) == 1

    @mock.patch(
        "cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml.GenerateAndLoadDataFromYaml._dataload"
    )
    def test_batching(self, _dataload):
        with temp_sqlite_database_url() as database_url:
            task = _make_task(
                GenerateAndLoadDataFromYaml,
                {
                    "options": {
                        "generator_yaml": simple_yaml,
                        "num_records": 14,
                        "batch_size": 6,
                        "database_url": database_url,
                        "num_records_tablename": "Account",
                        "data_generation_task": "cumulusci.tasks.bulkdata.generate_from_yaml.GenerateDataFromYaml",
                        "reset_oids": False,
                    }
                },
            )
            task()
            assert len(_dataload.mock_calls) == 3
            task = None  # clean up db?

            engine = create_engine(database_url)
            connection = engine.connect()
            records = list(connection.execute("select * from Account"))
            connection.close()
            assert len(records) == 14 % 6  # leftovers

    def test_mismatched_options(self):
        with self.assertRaises(TaskOptionsError) as e:
            task = _make_task(
                GenerateDataFromYaml,
                {"options": {"generator_yaml": sample_yaml, "num_records": 10}},
            )
            task()
        assert "without num_records_tablename" in str(e.exception)

    def generate_continuation_data(self):
        g = data_generator_runtime.Globals()
        o = data_generator_runtime.ObjectRow(
            "Account", {"Name": "Johnston incorporated", "id": 5}
        )
        g.register_object(o, "The Company")
        for i in range(0, 5):
            # burn through 5 imaginary accounts
            g.id_manager.generate_id("Account")
        return yaml.safe_dump(g)

    def test_with_continuation_file(self):
        continuation_data = self.generate_continuation_data()
        with temp_sqlite_database_url() as database_url:
            with temporary_file_path("cont.yml") as continuation_file_path:
                with open(continuation_file_path, "w") as continuation_file:
                    continuation_file.write(continuation_data)

                task = _make_task(
                    GenerateDataFromYaml,
                    {
                        "options": {
                            "generator_yaml": sample_yaml,
                            "database_url": database_url,
                            "mapping": vanilla_mapping_file,
                            "continuation_file": continuation_file_path,
                        }
                    },
                )
                task()
                rows = self.assertRowsCreated(database_url)
                assert dict(rows[0])["id"] == 6

    def test_with_nonexistent_continuation_file(self):
        with self.assertRaises(TaskOptionsError) as e:
            with temp_sqlite_database_url() as database_url:
                task = _make_task(
                    GenerateDataFromYaml,
                    {
                        "options": {
                            "generator_yaml": sample_yaml,
                            "database_url": database_url,
                            "mapping": vanilla_mapping_file,
                            "continuation_file": "/tmp/foobar/baz/jazz/continuation.yml",
                        }
                    },
                )
                task()
                rows = self.assertRowsCreated(database_url)
                assert dict(rows[0])["id"] == 6

        assert "jazz" in str(e.exception)
        assert "does not exist" in str(e.exception)

    def test_generate_continuation_file(self):
        with temporary_file_path("cont.yml") as temp_continuation_file:
            with temp_sqlite_database_url() as database_url:
                task = _make_task(
                    GenerateDataFromYaml,
                    {
                        "options": {
                            "generator_yaml": sample_yaml,
                            "database_url": database_url,
                            "generate_continuation_file": temp_continuation_file,
                        }
                    },
                )
                task()
            mapping = yaml.safe_load(open(temp_continuation_file))
            assert mapping  # internals of this file are not important to MetaCI
