import unittest
from pathlib import Path

from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.bulkdata.data_generation.generate_from_yaml import GenerateFromYaml

sample_yaml = Path(__file__).parent / "include_parent.yml"


class TestGenerateFromYamlTask(unittest.TestCase):
    def test_simple_task_run(self):
        task_options = {"generator_yaml": sample_yaml}

        cc_task = create_task(GenerateFromYaml, task_options)
        cc_task()
