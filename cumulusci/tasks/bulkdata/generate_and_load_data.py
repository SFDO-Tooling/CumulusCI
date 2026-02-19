import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Union

from sqlalchemy import MetaData, create_engine

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import import_global, process_bool_arg
from cumulusci.tasks.bulkdata import LoadData
from cumulusci.tasks.bulkdata.mapping_parser import (
    parse_from_yaml,
    validate_and_inject_mapping,
)
from cumulusci.tasks.bulkdata.step import DataOperationType
from cumulusci.tasks.bulkdata.utils import generate_batches
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class GenerateAndLoadData(BaseSalesforceApiTask):
    """Orchestrate creating tempfiles, generating data, loading data, cleaning up tempfiles and batching."""

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
        "working_directory": {
            "description": "Store temporary files in working_directory for easier debugging."
        },
        "validate_only": {
            "description": "Boolean: if True, only validate the generated mapping against the org schema without loading data. "
            "Defaults to False."
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

        self.num_records = int(num_records) if num_records is not None else None

        batch_size = self.options.get("batch_size", self.num_records)
        if batch_size is not None:
            self.batch_size = int(batch_size)

            if self.batch_size <= 0:
                raise TaskOptionsError("Batch size should be greater than zero")
        else:
            self.batch_size = None
        class_path = self.options.get("data_generation_task")
        if class_path:
            self.data_generation_task = import_global(class_path)
        else:
            raise TaskOptionsError("No data generation task specified")

        self.working_directory = self.options.get("working_directory", None)
        self.database_url = self.options.get("database_url")
        self.validate_only = process_bool_arg(self.options.get("validate_only", False))

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
            working_directory = self.options.get("working_directory")
            if working_directory:
                tempdir = Path(working_directory)
                tempdir.mkdir(exist_ok=True)

            # Route to validation flow if validate_only is True
            if self.validate_only:
                return self._run_validation(
                    database_url=self.database_url,
                    tempdir=self.working_directory or tempdir,
                    mapping_file=self.mapping_file,
                )

            # Normal data generation and loading flow
            if self.batch_size:
                batches = generate_batches(self.num_records, self.batch_size)
            else:
                batches = [(None, 0, 1)]
            results = []
            for current_batch_size, index, total_batches in batches:
                if total_batches > 1:
                    self.logger.info(
                        f"Generating a data batch, batch_size={current_batch_size} "
                        f"index={index} total_records={self.num_records}"
                    )
                res = self._generate_batch(
                    database_url=self.database_url,
                    tempdir=self.working_directory or tempdir,
                    mapping_file=self.mapping_file,
                    batch_size=current_batch_size,
                    index=index,
                    total_batches=total_batches,
                )
                results.append(res)
        self.return_values = {"load_results": results}
        return self.return_values

    def _datagen(self, subtask_options):
        task_config = TaskConfig({"options": subtask_options})
        data_gen_task = self.data_generation_task(
            self.project_config, task_config, org_config=self.org_config
        )
        data_gen_task()

    def _dataload(self, subtask_options) -> dict:
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
        return subtask.return_values

    def _generate_batch(
        self,
        *,
        database_url: Optional[str],
        tempdir: Union[Path, str, None],
        mapping_file: Union[Path, str, None],
        batch_size: Optional[int],
        index: int,
        total_batches: int,
    ) -> dict:
        """Generate a batch in database_url or a tempfile if it isn't specified."""
        # Setup and generate data
        subtask_options = self._setup_and_generate_data(
            database_url=database_url,
            tempdir=tempdir,
            mapping_file=mapping_file,
            num_records=batch_size,
            batch_index=index,
        )

        # Load the data
        return self._dataload(subtask_options)

    def _setup_engine(self, database_url):
        """Set up the database engine"""
        engine = create_engine(database_url)

        metadata = MetaData(engine)
        metadata.reflect()
        return engine, metadata

    def _setup_and_generate_data(
        self,
        *,
        database_url: Optional[str],
        tempdir: Union[Path, str, None],
        mapping_file: Union[Path, str, None],
        num_records: Optional[int],
        batch_index: int,
    ) -> dict:
        """Setup database and generate data, returning subtask options with mapping.

        Args:
            database_url: Database URL or None to create temp SQLite
            tempdir: Temporary directory for generated files
            mapping_file: Path to mapping file or None to generate
            num_records: Number of records to generate
            batch_index: Current batch number

        Returns:
            dict: subtask_options with mapping file path set
        """
        if not database_url:
            sqlite_path = Path(tempdir) / "generated_data.db"
            database_url = f"sqlite:///{sqlite_path}"

        self._cleanup_object_tables(*self._setup_engine(database_url))

        subtask_options = {
            **self.options,
            "mapping": mapping_file,
            "reset_oids": False,
            "database_url": database_url,
            "num_records": num_records,
            "current_batch_number": batch_index,
            "working_directory": tempdir,
        }

        # Generate mapping file if needed
        if not subtask_options.get("mapping"):
            temp_mapping = Path(tempdir) / "temp_mapping.yml"
            mapping_file = self.options.get("generate_mapping_file", temp_mapping)
            subtask_options["generate_mapping_file"] = mapping_file

        # Run data generation
        self._datagen(subtask_options)

        if not subtask_options.get("mapping"):
            subtask_options["mapping"] = subtask_options["generate_mapping_file"]

        return subtask_options

    def _run_validation(
        self,
        *,
        database_url: Optional[str],
        tempdir: Union[Path, str, None],
        mapping_file: Union[Path, str, None],
    ):
        """Run validation flow: generate data once and validate mapping.

        Args:
            database_url: Database URL or None to create temp SQLite
            tempdir: Temporary directory for generated files
            mapping_file: Path to mapping file or None to generate

        Returns:
            dict: return_values with validation_result
        """
        # Setup and generate minimal data to create mapping
        subtask_options = self._setup_and_generate_data(
            database_url=database_url,
            tempdir=tempdir,
            mapping_file=mapping_file,
            num_records=1,  # Generate minimal data just to create mapping
            batch_index=0,
        )

        # Validate the mapping
        validation_result = self._validate_mapping(subtask_options)

        self.return_values = {"validation_result": validation_result}
        return self.return_values

    def _validate_mapping(self, subtask_options):
        """Validate the mapping against the org schema without loading data."""
        mapping_file = subtask_options.get("mapping")
        if not mapping_file:
            raise TaskOptionsError("Mapping file path required for validation")

        self.logger.info(f"Validating mapping file: {mapping_file}")
        mapping = parse_from_yaml(mapping_file)

        validation_result = validate_and_inject_mapping(
            mapping=mapping,
            sf=self.sf,
            namespace=self.project_config.project__package__namespace,
            data_operation=DataOperationType.INSERT,
            inject_namespaces=self.options.get("inject_namespaces", False),
            drop_missing=self.options.get("drop_missing_schema", False),
            validate_only=True,
        )

        # Log summary message
        self.logger.info("")
        if validation_result and validation_result.has_errors():
            self.logger.error("== Validation Failed ==")
            self.logger.error(f"  Errors: {len(validation_result.errors)}")
            if validation_result.warnings:
                self.logger.warning(f"  Warnings: {len(validation_result.warnings)}")
        elif validation_result and validation_result.warnings:
            self.logger.warning("== Validation Successful (With Warnings) ==")
            self.logger.warning(f"  Warnings: {len(validation_result.warnings)}")
        else:
            self.logger.info("== Validation Successful ==")
        self.logger.info("")

        return validation_result

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
