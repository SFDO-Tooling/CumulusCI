import unittest
from unittest import mock
import pathlib

from cumulusci.tasks.bulkdata.data_generation.data_generator import generate
from cumulusci.tasks.bulkdata.data_generation.data_gen_exceptions import DataGenError

write_row_path = "cumulusci.tasks.bulkdata.data_generation.output_streams.DebugOutputStream.write_row"


class TestReferences(unittest.TestCase):
    @mock.patch(write_row_path)
    def test_included_file(self, write_row):
        include_parent = pathlib.Path(__file__).parent / "include_parent.yml"
        with open(include_parent) as f:
            generate(f, 1, {}, None, None)

        write_row.assert_called_with(
            "Account",
            {"id": 1, "name": "Default Company Name", "ShippingCountry": "Canada"},
        )

    @mock.patch(write_row_path)
    def test_failed_include_file(self, write_row):
        failed_include = pathlib.Path(__file__).parent / "include_bad_parent.yml"
        with self.assertRaises(DataGenError):
            with open(failed_include) as f:
                generate(f, 1, {}, None, None)
