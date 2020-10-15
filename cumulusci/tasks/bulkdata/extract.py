import itertools
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, MetaData, Table, Unicode
from sqlalchemy.orm import create_session, mapper

from cumulusci.core.exceptions import TaskOptionsError, BulkDataException
from cumulusci.tasks.bulkdata.utils import (
    SqlAlchemyMixin,
    create_table,
)
from cumulusci.core.utils import process_bool_arg

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.bulkdata.step import (
    DataOperationStatus,
    DataOperationType,
    get_query_operation,
)
from cumulusci.tasks.bulkdata.dates import (
    adjust_relative_dates,
)
from cumulusci.utils import os_friendly_path, log_progress
from cumulusci.tasks.bulkdata.mapping_parser import (
    parse_from_yaml,
    validate_and_inject_mapping,
)
from cumulusci.tasks.bulkdata.utils import consume


class ExtractData(SqlAlchemyMixin, BaseSalesforceApiTask):
    """Perform Bulk Queries to extract data for a mapping and persist to a SQL file or database."""

    task_options = {
        "database_url": {
            "description": "A DATABASE_URL where the query output should be written"
        },
        "mapping": {
            "description": "The path to a yaml file containing mappings of the database fields to Salesforce object fields",
            "required": True,
        },
        "sql_path": {
            "description": "If set, an SQL script will be generated at the path provided "
            + "This is useful for keeping data in the repository and allowing diffs."
        },
        "inject_namespaces": {
            "description": "If True, the package namespace prefix will be automatically added to objects "
            "and fields for which it is present in the org. Defaults to True."
        },
        "drop_missing_schema": {
            "description": "Set to True to skip any missing objects or fields instead of stopping with an error."
        },
    }

    def _init_options(self, kwargs):
        super(ExtractData, self)._init_options(kwargs)

        if self.options.get("database_url"):
            # prefer database_url if it's set
            self.options["sql_path"] = None
        elif self.options.get("sql_path"):
            self.options["sql_path"] = os_friendly_path(self.options["sql_path"])
        else:
            raise TaskOptionsError(
                "You must set either the database_url or sql_path option."
            )

        self.options["inject_namespaces"] = process_bool_arg(
            self.options.get("inject_namespaces", True)
        )
        self.options["drop_missing_schema"] = process_bool_arg(
            self.options.get("drop_missing_schema", False)
        )
        self._id_generators = {}

    def _run_task(self):
        self._init_mapping()
        with self._init_db():
            for mapping in self.mapping.values():
                self._run_query(mapping)

            self._map_autopks()

            if self.options.get("sql_path"):
                self._sqlite_dump()

    @contextmanager
    def _init_db(self):
        """Initialize the database and automapper."""
        self.models = {}

        with self._database_url() as database_url:

            # initialize the DB engine
            self.engine = create_engine(database_url)
            with self.engine.connect() as connection:

                # initialize DB metadata
                self.metadata = MetaData()
                self.metadata.bind = connection

                # Create the tables
                self._create_tables()

                # initialize session
                self.session = create_session(bind=connection, autocommit=False)

                yield self.session, self.metadata, connection

    def _init_mapping(self):
        """Load a YAML mapping file."""
        mapping_file_path = self.options["mapping"]
        self.logger.info(f"Mapping file: {mapping_file_path}")
        self.mapping = parse_from_yaml(mapping_file_path)

        validate_and_inject_mapping(
            mapping=self.mapping,
            org_config=self.org_config,
            namespace=self.project_config.project__package__namespace,
            data_operation=DataOperationType.QUERY,
            inject_namespaces=self.options["inject_namespaces"],
            drop_missing=self.options["drop_missing_schema"],
        )

    def _run_query(self, mapping):
        """Execute a Bulk or REST API query job and store the results."""
        step = get_query_operation(
            sobject=mapping.sf_object,
            api=mapping.api,
            fields=mapping.get_extract_field_list(),
            api_options={},
            context=self,
            query=mapping.get_soql(),
        )

        self.logger.info(f"Extracting data for sObject {mapping.sf_object}")
        step.query()

        if step.job_result.status is DataOperationStatus.SUCCESS:
            if step.job_result.records_processed:
                self.logger.info("Downloading and importing records")
                self._import_results(mapping, step)
            else:
                self.logger.info(f"No records found for sObject {mapping.sf_object}")
        else:
            raise BulkDataException(
                f"Unable to execute query: {','.join(step.job_result.job_errors)}"
            )

    def _log_progress_stream(self, mapping, generator):
        """Log progress, but without mutating records"""
        # TODO: log_progress needs to know our batch size, when made configurable.
        return log_progress(generator, self.logger)

    def _record_type_stream(self, mapping, record_iterator):
        """Add a static Record Type to each record"""
        if mapping.record_type:
            return (record + [mapping.record_type] for record in record_iterator)

        return record_iterator

    def _relative_dates_stream(self, mapping, record_iterator):
        """Convert relative dates to stable dates."""
        if mapping.anchor_date:
            date_context = mapping.get_relative_date_context(self.org_config)
            if date_context[0] or date_context[1]:
                return (
                    adjust_relative_dates(
                        mapping, date_context, record, DataOperationType.QUERY
                    )
                    for record in record_iterator
                )

        return record_iterator

    def _person_accounts_stream(self, mapping, record_iterator):
        """Set Name field as blank for Person Account "Account" records."""
        if (
            mapping.sf_object == "Account"
            and "Name" in mapping.fields
            and self.org_config.is_person_accounts_enabled
        ):
            Name_index = mapping.get_database_columns().index(
                mapping.get_extract_field_list().index("Name")
            )
            IsPersonAccount_index = mapping.get_database_columns().index(
                mapping.get_extract_field_list().index("IsPersonAccount")
            )

            def strip_name_field(record):
                nonlocal Name_index, IsPersonAccount_index
                if record[IsPersonAccount_index].lower() == "true":
                    record[Name_index] = ""
                return record

            record_iterator = (strip_name_field(record) for record in record_iterator)

    def _import_results(self, mapping, step):
        """Ingest results from the Bulk API query."""
        conn = self.session.connection()

        # Build our generator chain.
        record_iterator = step.get_results()
        record_iterator = self._log_progress_stream(mapping, record_iterator)
        record_iterator = self._record_type_stream(mapping, record_iterator)
        record_iterator = self._relative_dates_stream(mapping, record_iterator)

        # Split out the returned records into two separate streams and
        # load into the main table and the Id mapping table
        values, ids = itertools.tee(record_iterator)

        # Create two streams of synthetic Ids, returning the same values,
        # to populate this table and the global Id table.
        id_source_sobj, id_source_global = itertools.tee(
            self._id_generator_for_object(mapping.sf_object)
        )

        # Compose these generators into streams that can be directly
        # inserted into our database
        # Note: this relies on the invariant that the Id is extracted first,
        # which is enforced by the implementation of get_extract_field_list()
        f_ids = ((row[0], next(id_source_global)) for row in ids)
        f_values = ([next(id_source_sobj)] + row[1:] for row in values)

        values_chunks = self._sql_bulk_insert_from_records_incremental(
            connection=conn,
            table=mapping.table,
            columns=mapping.get_database_columns(),
            record_iterable=f_values,
        )
        ids_chunks = self._sql_bulk_insert_from_records_incremental(
            connection=conn,
            table=self.ID_TABLE_NAME,
            columns=["sf_id", "id"],
            record_iterable=f_ids,
        )

        # do the inserts one chunk at a time based on all of the
        # generators nested previously.
        consume(zip(values_chunks, ids_chunks))

        if "RecordTypeId" in mapping.fields:
            self._extract_record_types(
                mapping.sf_object, mapping.get_source_record_type_table(), conn
            )

        self.session.commit()

    def _map_autopks(self):
        """Convert Salesforce Ids to autopks"""
        for m in self.mapping.values():
            lookup_keys = list(m.lookups.keys())
            if lookup_keys:
                self._convert_lookups_to_id(m, lookup_keys)

        # Drop Salesforce Id table
        self.metadata.tables[self.ID_TABLE_NAME].drop()

    def _convert_lookups_to_id(self, mapping, lookup_keys):
        """Rewrite persisted Salesforce Ids to refer to auto-PKs."""
        for lookup_key in lookup_keys:
            lookup_info = mapping.lookups[lookup_key]
            model = self.models[mapping.table]
            key_field = lookup_info.get_lookup_key_field()

            self._update_sf_id_column(model, key_field)

        self.session.commit()

    def _create_tables(self):
        """Create a table for each mapping step."""
        for mapping in self.mapping.values():
            self._create_table(mapping)

        self._create_global_id_table()
        self.metadata.create_all()

    def _create_table(self, mapping):
        """Create a table for the given mapping."""
        model_name = f"{mapping.table}Model"
        mapper_kwargs = {}
        self.models[mapping.table] = type(model_name, (object,), {})

        t = create_table(mapping, self.metadata)

        if "RecordTypeId" in mapping.fields:
            # We're using Record Type Mapping support.
            # If multiple mappings point to the same table, don't recreate the table
            if mapping.get_source_record_type_table() not in self.models:
                self._create_record_type_table(mapping.get_source_record_type_table())

        mapper(self.models[mapping.table], t, **mapper_kwargs)

    def _create_global_id_table(self):
        sf_id_model_name = f"{self.ID_TABLE_NAME}Model"
        self.models[self.ID_TABLE_NAME] = type(sf_id_model_name, (object,), {})
        sf_id_fields = [
            Column("id", Unicode(255), primary_key=True),
            Column("sf_id", Unicode(24)),
        ]
        id_t = Table(self.ID_TABLE_NAME, self.metadata, *sf_id_fields)
        mapper(self.models[self.ID_TABLE_NAME], id_t)

    def _sqlite_dump(self):
        """Write a SQLite script output file."""
        path = self.options["sql_path"]
        with open(path, "w", encoding="utf-8") as f:
            for line in self.session.connection().connection.iterdump():
                f.write(line + "\n")
