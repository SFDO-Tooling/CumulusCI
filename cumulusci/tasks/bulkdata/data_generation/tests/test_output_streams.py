import unittest
from io import StringIO
import json
import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from contextlib import redirect_stdout

from sqlalchemy import create_engine

from cumulusci.tasks.bulkdata.data_generation.output_streams import (
    SqlOutputStream,
    JSONOutputStream,
    CSVOutputStream,
)

from cumulusci.tasks.bulkdata.data_generation.data_generator import generate
from cumulusci.tasks.bulkdata.data_generation.snowfakery import generate_cli


sample_yaml = Path(__file__).parent / "include_parent.yml"


class TestSqlOutputStream(unittest.TestCase):
    def test_flushes(self):
        yaml = """
        - object: foo
          count: 15
          fields:
            a: b
            c: 3
        - object: bar
          count: 1
        """

        class MockFlush:
            def __init__(self, real_flush):
                self.real_flush = real_flush
                self.flush_count = 0

            def __call__(self):
                self.flush_count += 1
                self.real_flush()

        with NamedTemporaryFile() as f:
            url = f"sqlite:///{f.name}"
            output_stream = SqlOutputStream.from_url(url, None)
            output_stream.flush_limit = 3
            real_flush = output_stream.flush
            output_stream.flush = MockFlush(real_flush)
            generate(StringIO(yaml), 1, {}, output_stream)
            assert output_stream.flush.flush_count == 5
            output_stream.close()

            engine = create_engine(url)
            connection = engine.connect()
            result = connection.execute("select * from foo")
            assert len(list(result)) == 15
            result = connection.execute("select * from bar")
            assert len(list(result)) == 1

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

            engine = create_engine(url)
            connection = engine.connect()
            result = connection.execute("select * from foo")
            assert tuple(dict(row) for row in result) == (
                {"id": 1, "a": "1", "b": None, "c": "3", "d": None},
                {"id": 2, "a": None, "b": "2", "c": None, "d": "4"},
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

        output_stream = JSONOutputStream(StringIO())
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
        x = StringIO()
        with redirect_stdout(x):
            generate_cli.callback(
                yaml_file=sample_yaml, output_format="json", output_files=["-"]
            )
        # TODO: more validation!

    def test_dates(self):
        yaml = """
        - object: foo
          fields:
            y2k: <<date(year=2000, month=1, day=1)>>
            party: <<datetime(year=1999, month=12, day=31, hour=23, minute=59, second=59)>>
            randodate:
                date_between:
                    start_date: 2000-02-02
                    end_date: 2010-01-01
        """
        stdout = StringIO()
        output_stream = JSONOutputStream(stdout)
        generate(StringIO(yaml), 1, {}, output_stream)
        output_stream.close()
        values = json.loads(stdout.getvalue())[0]
        assert values["y2k"] == str(datetime.date(year=2000, month=1, day=1))
        assert values["party"] == str(
            datetime.datetime(
                year=1999, month=12, day=31, hour=23, minute=59, second=59
            )
        )
        assert len(values["randodate"].split("-")) == 3
        assert values["randodate"].startswith("200")


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
