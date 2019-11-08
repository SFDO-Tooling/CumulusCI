import unittest
import pathlib

from cumulusci.tasks.bulkdata.data_generation.generate_from_yaml import _generate

dnd_test = pathlib.Path(__file__).parent / "CharacterGenTest.yml"
data_imports = pathlib.Path(__file__).parent / "BDI_Generator.yml"


# TODO: Add some assertions


class TestParseAndOutput(unittest.TestCase):
    def test_d_and_d(self):
        with open(dnd_test) as open_yaml_file:
            _generate(open_yaml_file, 1, {}, None, None)

    def test_data_imports(self):
        with open(data_imports) as open_yaml_file:
            _generate(open_yaml_file, 1, {}, None, None)
