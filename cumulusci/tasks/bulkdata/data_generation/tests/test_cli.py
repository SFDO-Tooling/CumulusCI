import unittest
from unittest import mock
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from io import StringIO
import json

import yaml
from click.exceptions import ClickException
from sqlalchemy import create_engine

from cumulusci.tasks.bulkdata.data_generation.snowfakery import generate_cli, eval_arg
from cumulusci.tasks.bulkdata.data_generation.data_gen_exceptions import DataGenError

sample_yaml = Path(__file__).parent / "include_parent.yml"
bad_sample_yaml = Path(__file__).parent / "include_bad_parent.yml"
sample_mapping_yaml = (
    Path(__file__).parent.parent.parent / "tests" / "mapping_vanilla_sf.yml"
)
sample_accounts_yaml = Path(__file__).parent / "gen_sf_standard_objects.yml"

write_row_path = "cumulusci.tasks.bulkdata.data_generation.output_streams.DebugOutputStream.write_single_row"


class TestGenerateFromCLI(unittest.TestCase):
    @mock.patch(write_row_path)
    def test_simple(self, write_row):
        generate_cli.callback(
            yaml_file=sample_yaml,
            count=1,
            option={},
            dburl=None,
            debug_internals=None,
            generate_cci_mapping_file=None,
        )
        assert write_row.mock_calls == [
            mock.call(
                "Account",
                {"id": 1, "name": "Default Company Name", "ShippingCountry": "Canada"},
            )
        ]

    def test_eval_arg(self):
        assert eval_arg("5") == 5
        assert eval_arg("abc") == "abc"

    @mock.patch(write_row_path)
    def test_counts(self, write_row):
        generate_cli.callback(
            yaml_file=sample_yaml,
            count=2,
            option={},
            dburl=None,
            debug_internals=None,
            generate_cci_mapping_file=None,
        )
        assert write_row.mock_calls == [
            mock.call(
                "Account",
                {"id": 1, "name": "Default Company Name", "ShippingCountry": "Canada"},
            ),
            mock.call(
                "Account",
                {"id": 2, "name": "Default Company Name", "ShippingCountry": "Canada"},
            ),
        ]

    @mock.patch(write_row_path)
    def test_with_option(self, write_row):
        with self.assertWarns(UserWarning):
            generate_cli.callback(
                yaml_file=sample_yaml,
                count=1,
                option={"xyzzy": "abcd"},
                dburl=None,
                debug_internals=None,
                generate_cci_mapping_file=None,
            )

    @mock.patch(write_row_path)
    def test_with_bad_dburl(self, write_row):
        with self.assertRaises(Exception):
            generate_cli.callback(
                yaml_file=sample_yaml,
                count=1,
                option={},
                dburl="xyzzy:////foo/bar/baz.com",
                debug_internals=None,
                generate_cci_mapping_file=None,
            )

    @mock.patch(write_row_path)
    def test_with_debug_flags_on(self, write_row):
        with NamedTemporaryFile(suffix=".yml") as t:
            generate_cli.callback(
                yaml_file=sample_yaml,
                count=1,
                option={},
                dburl=None,
                debug_internals=True,
                generate_cci_mapping_file=t.name,
                mapping_file=None,
            )
            assert yaml.safe_load(t.name)

    @mock.patch(write_row_path)
    def test_exception_with_debug_flags_on(self, write_row):
        with NamedTemporaryFile(suffix=".yml") as t:
            with self.assertRaises(DataGenError):
                generate_cli.callback(
                    yaml_file=bad_sample_yaml,
                    count=1,
                    option={},
                    dburl=None,
                    debug_internals=True,
                    generate_cci_mapping_file=t.name,
                )
                assert yaml.safe_load(t.name)

    @mock.patch(write_row_path)
    def test_exception_with_debug_flags_off(self, write_row):
        with NamedTemporaryFile(suffix=".yml") as t:
            with self.assertRaises(ClickException):
                generate_cli.callback(
                    yaml_file=bad_sample_yaml,
                    count=1,
                    option={},
                    dburl=None,
                    debug_internals=False,
                    generate_cci_mapping_file=t.name,
                )
                assert yaml.safe_load(t.name)

    def test_mutually_exclusive(self):
        with self.assertRaises(ClickException) as e:
            with TemporaryDirectory() as t:
                generate_cli.main(
                    [
                        str(sample_yaml),
                        "--dburl",
                        f"csvfile://{t}/csvoutput",
                        "--output-format",
                        "JSON",
                    ],
                    standalone_mode=False,
                )
        assert "mutually exclusive" in str(e.exception)

        with self.assertRaises(ClickException) as e:
            generate_cli.main(
                [
                    str(sample_yaml),
                    "--cci-mapping-file",
                    sample_mapping_yaml,
                    "--output-format",
                    "JSON",
                ],
                standalone_mode=False,
            )
        assert "apping file" in str(e.exception)

    def test_json(self):
        with mock.patch(
            "cumulusci.tasks.bulkdata.data_generation.snowfakery.sys.stdout",
            new=StringIO(),
        ) as fake_out:
            generate_cli.main(
                ["--output-format", "json", str(sample_yaml)], standalone_mode=False
            )
            assert json.loads(fake_out.getvalue()) == [
                {
                    "ShippingCountry": "Canada",
                    "_table": "Account",
                    "id": 1,
                    "name": "Default Company Name",
                }
            ]

    def test_mapping_file(self):
        with TemporaryDirectory() as t:
            url = f"sqlite:///{t}/foo.db"
            generate_cli.main(
                [
                    "--cci-mapping-file",
                    str(sample_mapping_yaml),
                    str(sample_accounts_yaml),
                    "--dburl",
                    url,
                ],
                standalone_mode=False,
            )

            engine = create_engine(url)
            connection = engine.connect()
            result = list(connection.execute("select * from Account"))
            assert result[0]["id"] == 1
            assert result[0]["BillingCountry"] == "Canada"

    def test_mapping_file_no_dburl(self):
        with self.assertRaises(ClickException):
            generate_cli.main(
                ["--mapping_file", str(sample_mapping_yaml), str(sample_yaml)],
                standalone_mode=False,
            )
