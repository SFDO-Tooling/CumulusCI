import unittest
from io import StringIO

import pytest

from cumulusci.tasks.bulkdata.data_generation.data_generator import (
    merge_options,
    generate,
)
from cumulusci.tasks.bulkdata.data_generation.data_gen_exceptions import (
    DataGenNameError,
)


class TestParseGenerator(unittest.TestCase):
    def test_merge_options(self):
        options_definitions = [
            {"option": "total_data_imports", "default": 16},
            {"option": "xyzzy", "default": "abcde"},
        ]
        user_options = {"total_data_imports": 4, "qwerty": "EBCDIC"}
        options, extra_options = merge_options(options_definitions, user_options)
        assert options == {"total_data_imports": 4, "xyzzy": "abcde"}
        assert extra_options == {"qwerty"}

    def test_missing_options(self):
        options_definitions = [
            {"option": "total_data_imports", "default": 16},
            {"option": "xyzzy"},
        ]
        user_options = {"total_data_imports": 4}
        with self.assertRaises(DataGenNameError) as e:
            options, extra_options = merge_options(options_definitions, user_options)
        assert "xyzzy" in str(e.exception)

    def test_extra_options_warning(self):
        yaml = """
        - option: total_data_imports
          default: 16
        """
        with pytest.warns(UserWarning, match="qwerty"):
            generate(StringIO(yaml), 1, {"qwerty": "EBCDIC"}, None, None)

    def test_missing_options_from_yaml(self):
        yaml = """
        - option: total_data_imports
          default: 16
        - option: xyzzy
        """
        with self.assertRaises(DataGenNameError) as e:
            generate(StringIO(yaml), 1, {"qwerty": "EBCDIC"}, None, None)
        assert "xyzzy" in str(e.exception)
