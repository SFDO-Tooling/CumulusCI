import unittest
from pathlib import Path

from cumulusci.tasks.bulkdata.tests.test_bulkdata import _make_task
from cumulusci.tasks.bulkdata.data_generation.generate_from_yaml import GenerateFromYaml

sample_yaml = Path(__file__).parent / "child.yml"
import yaml


class TestGenerateFromDataTask(unittest.TestCase):
    def test_no_options(self):
        with self.assertRaises(Exception):
            _make_task(GenerateFromYaml, {})

    def test_simple(self):
        with open(sample_yaml, "r") as s:
            yaml.safe_load(s)
        _make_task(
            GenerateFromYaml,
            {"options": {"generator_yaml": sample_yaml, "num_records": 10}},
        )
