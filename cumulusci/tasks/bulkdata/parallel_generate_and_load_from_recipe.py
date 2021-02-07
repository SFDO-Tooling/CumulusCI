from tempfile import TemporaryDirectory
from pathlib import Path

from cumulusci.core.tasks import BaseSalesforceTask
from cumulusci.tasks.bulkdata.generate_and_load_data_from_yaml import (
    GenerateAndLoadDataFromYaml,
)
from cumulusci.core.config import TaskConfig


bulkgen_task = "cumulusci.tasks.bulkdata.generate_from_yaml.GenerateDataFromYaml"


class ParallelGenerateAndLoadFromRecipe(BaseSalesforceTask):
    """Generate and load data from Snowfakery in as many batches as necessary"""

    task_options = {
        **GenerateAndLoadDataFromYaml.task_options,
        "segment_size": {
            "description": "How many records to generate in a single group. Generally much larger than 50k.",
            "required": False,
        },
    }
    del task_options["data_generation_task"]

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.options["segment_size"] = self.options.get("segment_size", 50_000)

    def _run_task(self, *args, **kwargs):
        with TemporaryDirectory() as shared_directory:
            sqlite_url = f"sqlite:///{shared_directory}"
            self._initialize_common_data(shared_directory, sqlite_url)

            continuation_file = Path(shared_directory) / "continuation.yml"
            assert continuation_file.exists(), breakpoint()
            # do one at a time at first
            self.execute_batch(continuation_file, sqlite_url)

    def _initialize_common_data(self, subdirectory: str, database_url: str):
        """Run the recipe once to initialize the IDs of "singleton objects" like GAUs and campaigns"""
        subtask_options = self.options.copy()
        subtask_options["num_records"] = None  # make the smallest batch possible
        subtask_options["working_directory"] = subdirectory
        task_config = TaskConfig({"options": subtask_options})
        initial_subtask = GenerateAndLoadDataFromYaml(
            self.project_config, task_config, org_config=self.org_config
        )
        initial_subtask()

    def execute_batch(continuation_file: str, sqlite_url: str):
        assert 0
