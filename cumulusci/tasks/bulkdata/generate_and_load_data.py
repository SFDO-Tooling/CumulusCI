import os
from tempfile import TemporaryDirectory
from pathlib import Path

from sqlalchemy import MetaData, create_engine

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.bulkdata import LoadData
from cumulusci.tasks.bulkdata.utils import generate_batches
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
    need more control than that. Existing data tables will be emptied before being refilled.
    Your database will be completely deleted!

    If you use database_url and batch_size together, latter batches will overwrite
    earlier batches in the database and the first batch will replace tables if they exist.

    A table mapping IDs to SFIds will persist across batches and will grow monotonically.

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
        "num_records_tablename": {
            "description": "Which table to count records in.",
            "required": False,
        },
        "batch_size": {
            "description": "How many records to create and load at a time.",
            "required": False,
        },
        "data_generation_task": {
            "description": "Fully qualified class path of a task to generate the data. Look at cumulusci.tasks.bulkdata.tests.dummy_data_factory to learn how to write them.",
            "required": True,
        },
        "data_generation_options": {
            "description": "Options to pass to the data generator.",
            "required": False,
        },
        "vars": {
            "description": "Variables that the generate or load tasks might need.",
        },
        "replace_database": {
            "description": "Confirmation that it is okay to delete the data in database_url",
        },
        "debug_dir": {
            "description": "Store temporary DB files in debug_dir for easier debugging."
        },
        **LoadData.task_options,
    }
    task_options["mapping"]["required"] = False

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        mapping_file = self.options.get("mapping", None)
        if mapping_file:
            self.mapping_file = os.path.abspath(mapping_file)
            if not os.path.exists(self.mapping_file):
                raise TaskOptionsError(f"{self.mapping_file} cannot be found.")
        else:
            self.mapping_file = None

        self.database_url = self.options.get("database_url")
        num_records = self.options.get("num_records")
        if not num_records:
            raise TaskOptionsError(
                "Please specify the number of records to generate with num_records"
            )
        self.num_records = int(num_records)
        self.batch_size = int(self.options.get("batch_size", self.num_records))
        if self.batch_size <= 0:
            raise TaskOptionsError("Batch size should be greater than zero")
        class_path = self.options.get("data_generation_task")
        if class_path:
            self.data_generation_task = import_global(class_path)
        else:
            raise TaskOptionsError("No data generation task specified")

        self.debug_dir = self.options.get("debug_dir", None)
        self.database_url = self.options.get("database_url")

        if self.database_url:
            engine, metadata = self._setup_engine(self.database_url)
            tables = metadata.tables

            if len(list(tables)) and not self.options.get("replace_database"):
                raise TaskOptionsError(
                    f"Database {self.database_url} has tables "
                    f"({list(tables)}) "
                    "but `replace_database` was not specified"
                )

    def _run_task(self):
        with TemporaryDirectory() as tempdir:
            for current_batch_size, index in generate_batches(
                self.num_records, self.batch_size
            ):
                self.logger.info(
                    f"Generating a data batch, batch_size={current_batch_size} "
                    f"index={index} total_records={self.num_records}"
                )
                self._generate_batch(
                    self.database_url,
                    self.debug_dir or tempdir,
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
        """Generate a batch in database_url or a tempfile if it isn't specified."""
        if not database_url:
            sqlite_path = Path(tempdir) / "generated_data.db"
            database_url = f"sqlite:///{sqlite_path}"

        self._cleanup_object_tables(*self._setup_engine(database_url))

        subtask_options = {
            **self.options,
            "mapping": mapping_file,
            "reset_oids": False,
            "database_url": database_url,
            "num_records": batch_size,
            "current_batch_number": index,
            "working_directory": tempdir,
        }

        # some generator tasks can generate the mapping file instead of reading it
        with TemporaryDirectory() as tempdir:
            if not subtask_options.get("mapping"):
                temp_mapping = Path(tempdir) / "temp_mapping.yml"
                mapping_file = self.options.get("generate_mapping_file", temp_mapping)
                subtask_options["generate_mapping_file"] = mapping_file
            self._datagen(subtask_options)
            if not subtask_options.get("mapping"):
                subtask_options["mapping"] = mapping_file
            self._dataload(subtask_options)

    def _setup_engine(self, database_url):
        """Set up the database engine"""
        engine = create_engine(database_url)

        metadata = MetaData(engine)
        metadata.reflect()
        return engine, metadata

    def _cleanup_object_tables(self, engine, metadata):
        """Delete all tables that do not relate to id->OID mapping"""
        tables = metadata.tables
        tables_to_drop = [
            table
            for tablename, table in tables.items()
            if not tablename.endswith("sf_ids")
        ]
        if tables_to_drop:
            metadata.drop_all(tables=tables_to_drop)
