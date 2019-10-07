import os
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.bulkdata import LoadData
from cumulusci.utils import temporary_dir
from cumulusci.core.config import TaskConfig
from cumulusci.core.utils import import_global
from cumulusci.core.exceptions import TaskOptionsError


class GenerateAndLoadData(BaseSalesforceApiTask):
    """ Orchestrate creating tempfiles, generating data, loading data, cleaning up tempfiles."""

    task_docs = """
    Use the `num_records` option to specify how many records to generate.
    Use the `mappings` option to specify a mapping file.
    Use 'data_generation_task' to specify what Python class to use to generate the data.'
    Use 'batch_size' to specify how many records to generate and upload in every batch.

    By default it creates the data in a temporary file and then cleans it up later. Specify database_url if you
    need more control than that. The use of both database_url and batch_size together is not currently supported.
    """

    task_options = {
        "num_records": {
            "description": "How many records to generate. Precise calcuation depends on the generator.",
            "required": True,
        },
        "batch_size": {
            "description": "How many records to create and load at a time..",
            "required": False,
        },
        "mapping": {"description": "A mapping YAML file to use", "required": True},
        "data_generation_task": {
            "description": "Fully qualified class path of a task to generate the data. Use cumulusci.tasks.bulkdata.factory_generator if you would like to use a Factory Module.",
            "required": False,
        },
        "data_generation_options": {
            "description": "Options to pass to the data generator.",
            "required": False,
        },
        "database_url": {
            "description": "A URL to store the database (defaults to a transient SQLite file)",
            "required": "",
        },
    }

    def _run_task(self):
        mapping_file = os.path.abspath(self.options["mapping"])
        assert os.path.exists(mapping_file), f"{mapping_file} cannot be found."
        database_url = self.options.get("database_url")
        num_records = int(self.options["num_records"])
        batch_size = int(self.options.get("batch_size", num_records))
        if database_url and batch_size != num_records:
            raise TaskOptionsError(
                "You may not specify both `database_url` and `batch_size` options."
            )

        with temporary_dir() as tempdir:
            num_batches = (num_records // batch_size) + 1
            for i in range(0, num_batches):
                if i == num_batches - 1:  # last batch
                    batch_size = num_records - (batch_size * i)  # leftovers
                if batch_size > 0:
                    self._generate_batch(
                        database_url, tempdir, mapping_file, batch_size, i
                    )

    def _datagen(self, subtask_options):
        class_path = self.options.get("data_generation_task", None)
        task_class = import_global(class_path)
        task_config = TaskConfig({"options": subtask_options})
        data_gen_task = task_class(
            self.project_config, task_config, org_config=self.org_config
        )
        data_gen_task()

    def _dataload(self, subtask_options):
        subtask_config = TaskConfig({"options": subtask_options})
        subtask = LoadData(
            project_config=self.project_config,
            task_config=subtask_config,
            org_config=self.org_config,
            flow=self.flow,
            name=self.name,
            stepnum=self.stepnum,
        )
        subtask()

    def _generate_batch(self, database_url, tempdir, mapping_file, batch_size, index):
        if not database_url:
            sqlite_path = os.path.join(tempdir, f"generated_data_{index}.db")
            database_url = f"sqlite:///" + sqlite_path
        subtask_options = {
            **self.options,
            "mapping": mapping_file,
            "database_url": database_url,
            "num_records": batch_size,
        }
        self._datagen(subtask_options)
        self._dataload(subtask_options)
