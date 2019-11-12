from io import StringIO
import unittest
import mock

from cumulusci.tasks.bulkdata.data_generation.data_generator import generate

write_row_path = "cumulusci.tasks.bulkdata.data_generation.output_streams.DebugOutputStream.write_row"
faker_path = ""


class TestFaker(unittest.TestCase):
    @mock.patch(write_row_path)
    def test_fake_block_simple(self, write_row_mock):
        yaml = """
        - object: OBJ
          fields:
            first_name:
                fake:
                    first_name
        """
        generate(StringIO(yaml), 1, {}, None, None)
        assert write_row_mock.mock_calls[0].args[1]["first_name"]

    @mock.patch(write_row_path)
    def test_fake_block_simple_oneline(self, write_row_mock):
        yaml = """
        - object: OBJ
          fields:
            first_name:
                fake: first_name
        """
        generate(StringIO(yaml), 1, {}, None, None)
        assert write_row_mock.mock_calls[0].args[1]["first_name"]

    @mock.patch(write_row_path)
    def test_fake_block_one_param(self, write_row_mock):
        yaml = """
        - object: OBJ
          fields:
            country:
                fake.country_code:
                    representation: alpha-2
        """
        generate(StringIO(yaml), 1, {}, None, None)
        assert len(write_row_mock.mock_calls[0].args[1]["country"]) == 2

    @mock.patch(write_row_path)
    def test_fake_inline(self, write_row_mock):
        yaml = """
        - object: OBJ
          fields:
            country: <<fake.country_code(representation='alpha-2')>>
        """
        generate(StringIO(yaml), 1, {}, None, None)
        assert len(write_row_mock.mock_calls[0].args[1]["country"]) == 2

    @mock.patch(write_row_path)
    def test_fake_two_params_flat(self, write_row_mock):
        yaml = """
        - object: OBJ
          fields:
            date: <<fake.date(pattern="%Y-%m-%d", end_datetime=None)>>
        """
        generate(StringIO(yaml), 1, {}, None, None)
        assert len(write_row_mock.mock_calls[0].args[1]["date"].split("-")) == 3

    @mock.patch(write_row_path)
    def test_fake_two_params_nested(self, write_row_mock):
        yaml = """
        - object: OBJ
          fields:
            date:
                fake.date_between:
                    start_date: -10y
                    end_date: today
        """
        generate(StringIO(yaml), 1, {}, None, None)
        assert write_row_mock.mock_calls[0].args[1]["date"].year
