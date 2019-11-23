import unittest
from unittest import mock
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml
from click.exceptions import ClickException

from cumulusci.tasks.bulkdata.data_generation.data_generator_cli import generate_cli
from cumulusci.tasks.bulkdata.data_generation.data_gen_exceptions import DataGenError

sample_yaml = Path(__file__).parent / "include_parent.yml"
bad_sample_yaml = Path(__file__).parent / "include_bad_parent.yml"

write_row_path = "cumulusci.tasks.bulkdata.data_generation.output_streams.DebugOutputStream.write_row"


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
