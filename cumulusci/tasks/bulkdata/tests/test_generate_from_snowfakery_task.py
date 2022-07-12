from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pytest
import yaml
from sqlalchemy import create_engine

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from cumulusci.tasks.bulkdata.tests.utils import _make_task

sample_yaml = Path(__file__).parent / "snowfakery/gen_npsp_standard_objects.recipe.yml"
simple_yaml = Path(__file__).parent / "snowfakery/include_parent.yml"
simple_snowfakery_yaml = (
    Path(__file__).parent / "snowfakery/simple_snowfakery.recipe.yml"
)

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


@contextmanager
def run_task(task=GenerateDataFromYaml, **options):
    with temp_sqlite_database_url() as database_url:
        options["database_url"] = database_url
        task = _make_task(task, {"options": options})
        task()
        yield database_url


class TestGenerateFromDataTask:
    def assertRowsCreated(self, database_url):
        engine = create_engine(database_url)
        connection = engine.connect()
        accounts = connection.execute("select * from Account")
        accounts = list(accounts)
        assert accounts and accounts[0] and accounts[0][1]
        return accounts

    def test_no_options(self):
        with pytest.raises(Exception):
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
        with pytest.raises(TaskOptionsError):
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
            with pytest.warns(UserWarning):
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
                        "database_url": database_url,
                    }
                },
            )
            task()
            assert len(self.assertRowsCreated(database_url)) == 1, len(
                self.assertRowsCreated(database_url)
            )

    @mock.patch(
        "cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml.GenerateAndLoadDataFromYaml._dataload"
    )
    def test_simple_generate_and_load_with_numrecords(self, _dataload):
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

    @mock.patch("cumulusci.tasks.bulkdata.generate_from_yaml.generate_data")
    def test_exception_handled_cleanly(self, generate_data):
        generate_data.side_effect = AssertionError("Foo")
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
        assert len(generate_data.mock_calls) == 1

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
        with pytest.raises(TaskOptionsError) as e:
            task = _make_task(
                GenerateDataFromYaml,
                {"options": {"generator_yaml": sample_yaml, "num_records": 10}},
            )
            task()
        assert "without num_records_tablename" in str(e.value)

    def test_with_nonexistent_continuation_file(self):
        with pytest.raises(TaskOptionsError) as e:
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

        assert "jazz" in str(e.value)
        assert "does not exist" in str(e.value)

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
            continuation_file = yaml.safe_load(open(temp_continuation_file))
            assert continuation_file  # internals of this file are not important to CumulusCI

    def _get_mapping_file(self, **options):
        with temporary_file_path("mapping.yml") as temp_mapping:
            with temp_sqlite_database_url() as database_url:
                task = _make_task(
                    GenerateDataFromYaml,
                    {
                        "options": {
                            "database_url": database_url,
                            "generate_mapping_file": temp_mapping,
                            **options,
                        }
                    },
                )
                task()
            with open(temp_mapping) as f:
                mapping = yaml.safe_load(f)
        return mapping

    def test_generate_mapping_file__loadfile__inferred(self):
        mapping = self._get_mapping_file(generator_yaml=simple_snowfakery_yaml)

        assert mapping["Insert Account"]["api"] == "bulk"
        assert mapping["Insert Contact"].get("bulk_mode") is None
        assert list(mapping.keys()) == ["Insert Account", "Insert Contact"]

    def test_generate_mapping_file__loadfile__overridden(self):
        loading_rules = str(simple_snowfakery_yaml).replace(
            ".recipe.yml", "_2.load.yml"
        )
        mapping = self._get_mapping_file(
            generator_yaml=simple_snowfakery_yaml, loading_rules=str(loading_rules)
        )

        assert mapping["Insert Account"].get("api") is None
        assert mapping["Insert Contact"]["bulk_mode"].lower() == "parallel"
        assert list(mapping.keys()) == ["Insert Contact", "Insert Account"]

    def test_generate_mapping_file__loadfile_multiple_files(self):
        loading_rules = (
            str(simple_snowfakery_yaml).replace(".recipe.yml", "_2.load.yml")
            + ","
            + str(simple_snowfakery_yaml).replace(".recipe.yml", ".load.yml")
        )
        mapping = self._get_mapping_file(
            generator_yaml=simple_snowfakery_yaml, loading_rules=str(loading_rules)
        )

        assert mapping["Insert Account"]["api"] == "bulk"
        assert mapping["Insert Contact"]["bulk_mode"].lower() == "parallel"
        assert list(mapping.keys()) == ["Insert Contact", "Insert Account"]

    def test_generate_mapping_file__loadfile_missing(self):
        loading_rules = str(simple_snowfakery_yaml).replace(
            ".recipe.yml", "_3.load.yml"
        )
        with pytest.raises(FileNotFoundError):
            self._get_mapping_file(
                generator_yaml=simple_snowfakery_yaml, loading_rules=str(loading_rules)
            )
