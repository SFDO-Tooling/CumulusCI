import unittest
from unittest import mock
from pathlib import Path
from tempfile import NamedTemporaryFile

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.tests.utils import _make_task

import yaml
from sqlalchemy import create_engine

try:
    import snowfakery
    from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
        GenerateAndLoadDataFromYaml,
    )
except ImportError:
    snowfakery = None

if snowfakery:
    sample_yaml = (
        Path(snowfakery.__file__).parent / "../tests/gen_npsp_standard_objects.yml"
    )
    simple_yaml = Path(snowfakery.__file__).parent / "../tests/include_parent.yml"
    from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml

vanilla_mapping_file = Path(__file__).parent / "../../tests/mapping_vanilla_sf.yml"


@unittest.skipUnless(snowfakery, "Snowfakery not installed")
class TestGenerateFromDataTask(unittest.TestCase):
    def assertRowsCreated(self, database_url):
        engine = create_engine(database_url)
        connection = engine.connect()
        accounts = connection.execute(f"select * from Account")
        accounts = list(accounts)
        assert accounts and accounts[0] and accounts[0][1]
        return accounts

    def test_no_options(self):
        with self.assertRaises(Exception):
            _make_task(GenerateDataFromYaml, {})

    def test_simple(self):
        with NamedTemporaryFile() as t:
            database_url = f"sqlite:///{t.name}"
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
        with NamedTemporaryFile() as t:
            database_url = f"sqlite:///{t.name}"
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
        with NamedTemporaryFile() as temp_mapping:
            with NamedTemporaryFile() as temp_db:
                database_url = f"sqlite:///{temp_db.name}"
                task = _make_task(
                    GenerateDataFromYaml,
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
        with NamedTemporaryFile() as t:
            database_url = f"sqlite:///{t.name}"
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
    def test_batching(self, _dataload):
        with NamedTemporaryFile() as t:
            database_url = f"sqlite:///{t.name}"
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

            engine = create_engine(database_url)
            connection = engine.connect()
            records = list(connection.execute("select * from Account"))
            assert len(records) == 14 % 6  # leftovers

    def test_mismatched_options(self):
        with self.assertRaises(TaskOptionsError) as e:
            task = _make_task(
                GenerateDataFromYaml,
                {"options": {"generator_yaml": sample_yaml, "num_records": 10}},
            )
            task()
        assert "without num_records_tablename" in str(e.exception)

    def test_with_continuation_file(self):
        continuation_data = """
!snowfakery_globals
id_manager: !snowfakery_ids
  last_used_ids:
    Account: 5
last_seen_obj_of_type:
  Account: &id001 !snowfakery_objectrow
    _tablename: Account
    _values:
      Name: Johnston incorporated
      id: 5
named_objects:
  blah: blah
        """

        with NamedTemporaryFile() as temp_db:
            database_url = f"sqlite:///{temp_db.name}"
            with NamedTemporaryFile("w+") as continuation_file:
                continuation_file.write(continuation_data)
                continuation_file.flush()
                task = _make_task(
                    GenerateDataFromYaml,
                    {
                        "options": {
                            "generator_yaml": sample_yaml,
                            "database_url": database_url,
                            "mapping": vanilla_mapping_file,
                            "continuation_file": continuation_file.name,
                        }
                    },
                )
                task()
                rows = self.assertRowsCreated(database_url)
                assert dict(rows[0])["id"] == 6

    def test_with_nonexistent_continuation_file(self):
        with self.assertRaises(TaskOptionsError) as e:
            with NamedTemporaryFile() as temp_db:
                database_url = f"sqlite:///{temp_db.name}"
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
        with NamedTemporaryFile() as temp_continuation_file:
            with NamedTemporaryFile() as temp_db:
                database_url = f"sqlite:///{temp_db.name}"
                task = _make_task(
                    GenerateDataFromYaml,
                    {
                        "options": {
                            "generator_yaml": sample_yaml,
                            "database_url": database_url,
                            "generate_continuation_file": temp_continuation_file.name,
                        }
                    },
                )
                task()
            mapping = yaml.safe_load(open(temp_continuation_file.name))
            assert mapping  # internals of this file are not important to MetaCI
