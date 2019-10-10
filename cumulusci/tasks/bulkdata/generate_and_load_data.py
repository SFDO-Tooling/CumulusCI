import os
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.bulkdata import LoadData
from cumulusci.tasks.bulkdata.utils import generate_batches
from cumulusci.utils import temporary_dir
from cumulusci.core.config import TaskConfig
from cumulusci.core.utils import import_global
from cumulusci.core.exceptions import TaskOptionsError


class GenerateAndLoadData(BaseSalesforceApiTask):
    """ Orchestrate creating tempfiles, generating data, loading data, cleaning up tempfiles and batching."""

    task_docs = """
    Orchestrate creating tempfiles, generating data, loading data, cleaning up tempfiles and batching.

    CCI has features for generating data and for loading them into orgs. This task pulls them
    together to give some useful additional features, such as storing the intermediate data in
    a tempfile (the default behavior) and generating the data in batches instead of all at
    once (controlled by the `batch_size` option).

    The simplest possible usage is to specify the number of records you'd like generated, a
    mapping file that defines the schema and a data generation task written in Python to actually
    generate the data.

    Use the `num_records` option to specify how many records to generate.
    Use the `mapping` option to specify a mapping file.
    Use 'data_generation_task' to specify what Python class to use to generate the data.'
    Use 'batch_size' to specify how many records to generate and upload in every batch.

    By default it creates the data in a temporary file and then cleans it up later. Specify database_url if you
    need more control than that. The use of both database_url and batch_size together is not currently supported.

    If your generator class makes heavy use of Faker, you might be interested in this patch
    which frequently speeds Faker up. Adding that code to the bottom of your generator file may
    help accelerate it.

    https://sfdc.co/bwKxDD
    """

    task_options = {
        "num_records": {
            "description": "How many records to generate. Precise calcuation depends on the generator.",
            "required": True,
        },
        "batch_size": {
            "description": "How many records to create and load at a time.",
            "required": False,
        },
        "mapping": {"description": "A mapping YAML file to use", "required": True},
        "data_generation_task": {
            "description": "Fully qualified class path of a task to generate the data. Look at cumulusci.tasks.bulkdata.tests.dummy_data_factory to learn how to write them.",
            "required": True,
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

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.mapping_file = os.path.abspath(self.options["mapping"])
        if not os.path.exists(self.mapping_file):
            raise TaskOptionsError(f"{self.mapping_file} cannot be found.")
        self.database_url = self.options.get("database_url")
        self.num_records = int(self.options["num_records"])
        self.batch_size = int(self.options.get("batch_size", self.num_records))
        if self.batch_size <= 0:
            raise TaskOptionsError("Batch size should be greater than zero")
        self.class_path = self.options.get("data_generation_task")
        self.data_generation_task = import_global(self.class_path)

        if self.database_url and self.batch_size != self.num_records:
            raise TaskOptionsError(
                "You may not specify both `database_url` and `batch_size` options."
            )

    def _run_task(self):
        with temporary_dir() as tempdir:
            for current_batch_size, index in generate_batches(
                self.num_records, self.batch_size
            ):
                self._generate_batch(
                    self.database_url,
                    tempdir,
                    self.mapping_file,
                    current_batch_size,
                    index,
                )

    def _datagen(self, subtask_options):
        task_config = TaskConfig({"options": subtask_options})
        data_gen_task = self.data_generation_task(
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
            "current_batch_number": index,
        }
        self._datagen(subtask_options)
        self._dataload(subtask_options)
