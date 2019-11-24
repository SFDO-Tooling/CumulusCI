import unittest
from io import StringIO
import json
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from cumulusci.tasks.bulkdata.data_generation.output_streams import (
    SqlOutputStream,
    JSONOutputStream,
    CSVOutputStream,
)

from cumulusci.tasks.bulkdata.data_generation.data_generator import generate
from cumulusci.tasks.bulkdata.data_generation.data_generator_cli import generate_cli


sample_yaml = Path(__file__).parent / "include_parent.yml"


class TestSqlOutputStream(unittest.TestCase):
    def test_flushes(self):
        yaml = """
        - object: foo
          count: 15
          fields:
            a: b
            c: 3
        """
        flush_count = 0
        real_flush = None

        def mock_flush():
            nonlocal flush_count
            flush_count += 1
            real_flush()

        with NamedTemporaryFile() as f:
            output_stream = SqlOutputStream.from_url(f"sqlite:///{f.name}", None)
            output_stream.flush_limit = 3
            real_flush = output_stream.flush
            output_stream.flush = mock_flush
            generate(StringIO(yaml), 1, {}, output_stream)
            assert flush_count == 3
            output_stream.close()

    def test_inferred_schema(self):
        yaml = """
        - object: foo
          fields:
            a: 1
            c: 3
        - object: foo
          fields:
            b: 2
            d: 4
        """
        with NamedTemporaryFile() as f:
            url = f"sqlite:///{f.name}"
            output_stream = SqlOutputStream.from_url(url, None)
            generate(StringIO(yaml), 1, {}, output_stream)
            output_stream.close()
            from sqlalchemy import create_engine

            engine = create_engine(url)
            connection = engine.connect()
            result = connection.execute("select * from foo")
            assert tuple(dict(row) for row in result) == (
                {"id": 1, "a": "1.0", "b": None, "c": "3.0", "d": None},
                {"id": 2, "a": None, "b": "2.0", "c": None, "d": "4.0"},
            )


class TestJSONOutputStream(unittest.TestCase):
    def test_json_output_real(self):
        yaml = """
        - object: foo
          count: 15
          fields:
            a: b
            c: 3
        """
        from sys import stdout

        output_stream = JSONOutputStream(stdout)
        generate(StringIO(yaml), 1, {}, output_stream)
        output_stream.close()

    def test_json_output_mocked(self):
        yaml = """
        - object: foo
          count: 2
          fields:
            a: b
            c: 3
        """

        stdout = StringIO()
        output_stream = JSONOutputStream(stdout)
        generate(StringIO(yaml), 1, {}, output_stream)
        output_stream.close()
        assert json.loads(stdout.getvalue()) == [
            {"_table": "foo", "a": "b", "c": 3.0, "id": 1},
            {"_table": "foo", "a": "b", "c": 3.0, "id": 2},
        ]

    def test_from_cli(self):
        generate_cli.callback(yaml_file=sample_yaml, output_format="json")


class TestCSVOutputStream(unittest.TestCase):
    def test_csv_output(self):
        yaml = """
        - object: foo
          fields:
            a: 1
            c: 3
        - object: foo
          fields:
            b: 2
            d: 4
        - object: bar
          fields:
            barb: 2
            bard: 4
        """
        with TemporaryDirectory() as t:
            output_stream = CSVOutputStream(f"csv://{t}/csvoutput")
            generate(StringIO(yaml), 1, {}, output_stream)
            output_stream.close()
            assert (Path(t) / "csvoutput" / "foo.csv").exists()
            with open(Path(t) / "csvoutput" / "csvw_metadata.json") as f:
                metadata = json.load(f)
                assert {table["url"] for table in metadata["tables"]} == {
                    "foo.csv",
                    "bar.csv",
                }

    def test_from_cli(self):
        with TemporaryDirectory() as t:
            generate_cli.main(
                [str(sample_yaml), "--dburl", f"csvfile://{t}/csvoutput"],
                standalone_mode=False,
            )
            assert (Path(t) / "csvoutput" / "Account.csv").exists()
            with open(Path(t) / "csvoutput" / "csvw_metadata.json") as f:
                metadata = json.load(f)
                assert {table["url"] for table in metadata["tables"]} == {"Account.csv"}
