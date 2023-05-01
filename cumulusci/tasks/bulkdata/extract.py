import itertools
import re
from contextlib import contextmanager

from sqlalchemy import Column, Integer, MetaData, Table, Unicode, create_engine
from sqlalchemy.orm import create_session, mapper

from cumulusci.core.exceptions import BulkDataException, TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.bulkdata.dates import adjust_relative_dates
from cumulusci.tasks.bulkdata.mapping_parser import (
    parse_from_yaml,
    validate_and_inject_mapping,
)
from cumulusci.tasks.bulkdata.step import (
    DataOperationStatus,
    DataOperationType,
    get_query_operation,
)
from cumulusci.tasks.bulkdata.utils import (
    SqlAlchemyMixin,
    consume,
    create_table,
    sql_bulk_insert_from_records,
    sql_bulk_insert_from_records_incremental,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import log_progress


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
            "description": "If True, the package namespace prefix will be "
            "automatically added to (or removed from) objects "
            "and fields based on the name used in the org. Defaults to True."
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
        elif not self.options.get("sql_path"):
            raise TaskOptionsError(
                "You must set either the database_url or sql_path option."
            )

        inject_namespaces = self.options.get("inject_namespaces")
        self.options["inject_namespaces"] = process_bool_arg(
            True if inject_namespaces is None else inject_namespaces
        )
        self.options["drop_missing_schema"] = process_bool_arg(
            self.options.get("drop_missing_schema") or False
        )

    def _run_task(self):
        self._init_mapping()
        with self._init_db():
            for mapping in self.mapping.values():
                soql = self._soql_for_mapping(mapping)
                self._run_query(soql, mapping)

            self._map_autopks()

            if self.options.get("sql_path"):
                self._sqlite_dump()

    @contextmanager
    def _init_db(self):
        """Initialize the database and automapper."""
        self.models = {}

        with self._database_url() as database_url:

            # initialize the DB engine
            parent_engine = create_engine(database_url)
            with parent_engine.connect() as connection:
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
        if not mapping_file_path:
            raise TaskOptionsError("Mapping file path required")
        self.logger.info(f"Mapping file: {self.options['mapping']}")

        self.mapping = parse_from_yaml(mapping_file_path)

        validate_and_inject_mapping(
            mapping=self.mapping,
            sf=self.sf,
            namespace=self.project_config.project__package__namespace,
            data_operation=DataOperationType.QUERY,
            inject_namespaces=self.options["inject_namespaces"],
            drop_missing=self.options["drop_missing_schema"],
            org_has_person_accounts_enabled=self.org_config.is_person_accounts_enabled,
        )

    def _soql_for_mapping(self, mapping):
        """Return a SOQL query suitable for extracting data for this mapping."""
        sf_object = mapping.sf_object
        fields = mapping.get_complete_field_map(include_id=True).keys()
        soql = f"SELECT {', '.join(fields)} FROM {sf_object}"

        if mapping.record_type:
            soql += f" WHERE RecordType.DeveloperName = '{mapping.record_type}'"

        if mapping.soql_filter is not None:
            soql = self.append_filter_clause(
                soql=soql, filter_clause=mapping.soql_filter
            )

        return soql

    def _run_query(self, soql, mapping):
        """Execute a Bulk or REST API query job and store the results."""

        step = get_query_operation(
            sobject=mapping.sf_object,
            api=mapping.api,
            fields=list(mapping.get_complete_field_map(include_id=True).keys()),
            api_options={},
            context=self,
            query=soql,
        )

        self.logger.info(f"Extracting data for sObject {mapping['sf_object']}")
        step.query()

        if step.job_result.status is DataOperationStatus.SUCCESS:
            if step.job_result.records_processed:
                self.logger.info("Downloading and importing records")
                self._import_results(mapping, step)
            else:
                self.logger.info(f"No records found for sObject {mapping['sf_object']}")
        else:
            raise BulkDataException(
                f"Unable to execute query: {','.join(step.job_result.job_errors)}"
            )

    def _import_results(self, mapping, step):
        """Ingest results from the Bulk API query."""
        conn = self.session.connection()

        # Map SF field names to local db column names
        field_map = mapping.get_complete_field_map(include_id=True)
        columns = [field_map[f] for f in field_map]  # Get values in insertion order.

        record_type = mapping.record_type
        if record_type:
            columns.append("record_type")

        # TODO: log_progress needs to know our batch size, when made configurable.
        record_iterator = log_progress(step.get_results(), self.logger)
        if record_type:
            record_iterator = (record + [record_type] for record in record_iterator)

        # Convert relative dates to stable dates.
        if mapping.anchor_date:
            date_context = mapping.get_relative_date_context(
                list(field_map.keys()), self.sf
            )
            if date_context[0] or date_context[1]:
                record_iterator = (
                    adjust_relative_dates(
                        mapping, date_context, record, DataOperationType.QUERY
                    )
                    for record in record_iterator
                )

        # Set Name field as blank for Person Account "Account" records.
        if (
            mapping.sf_object == "Account"
            and "Name" in field_map
            and self.org_config.is_person_accounts_enabled
        ):
            # Bump indices by one since record's ID is the first column.
            Name_index = columns.index(mapping.fields["Name"])
            IsPersonAccount_index = columns.index(mapping.fields["IsPersonAccount"])

            def strip_name_field(record):
                nonlocal Name_index, IsPersonAccount_index
                if record[IsPersonAccount_index].lower() == "true":
                    record[Name_index] = ""
                return record

            record_iterator = (strip_name_field(record) for record in record_iterator)

        if mapping.get_oid_as_pk():
            sql_bulk_insert_from_records(
                connection=conn,
                table=self.metadata.tables[mapping.table],
                columns=columns,
                record_iterable=record_iterator,
            )
        else:
            # If using the autogenerated id field, split out the returned records
            # into two separate streams and load into the main table and the sf_id_table
            values, ids = itertools.tee(record_iterator)
            f_values = (row[1:] for row in values)
            f_ids = (row[:1] for row in ids)

            values_chunks = sql_bulk_insert_from_records_incremental(
                connection=conn,
                table=self.metadata.tables[mapping.table],
                columns=columns[1:],  # Strip off the Id column
                record_iterable=f_values,
            )
            ids_chunks = sql_bulk_insert_from_records_incremental(
                connection=conn,
                table=self.metadata.tables[mapping.get_sf_id_table()],
                columns=["sf_id"],
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
        # Convert Salesforce Ids to autopks
        for m in self.mapping.values():
            lookup_keys = list(m.lookups.keys())
            if not m.get_oid_as_pk():
                if lookup_keys:
                    self._convert_lookups_to_id(m, lookup_keys)

        # Drop sf_id tables
        for m in self.mapping.values():
            if not m.get_oid_as_pk():
                self.metadata.tables[m.get_sf_id_table()].drop()

    def _get_mapping_for_table(self, table):
        """Return the first mapping for a table name"""
        for mapping in self.mapping.values():
            if mapping["table"] == table:
                return mapping

    def _convert_lookups_to_id(self, mapping, lookup_keys):
        """Rewrite persisted Salesforce Ids to refer to auto-PKs."""

        def throw(string):  # pragma: no cover
            raise BulkDataException(string)

        for lookup_key in lookup_keys:
            lookup_info = mapping.lookups.get(lookup_key) or throw(
                f"Cannot find lookup info {lookup_key}"
            )
            model = self.models.get(mapping.table)

            lookup_mapping = self._get_mapping_for_table(lookup_info.table) or throw(
                f"Cannot find lookup mapping for {lookup_info.table}"
            )

            lookup_model = self.models.get(lookup_mapping.get_sf_id_table())

            key_field = lookup_info.get_lookup_key_field()

            key_attr = getattr(model, key_field, None) or throw(
                f"key_field {key_field} not found in table {mapping.table}"
            )
            try:
                self.session.query(model).filter(
                    key_attr.isnot(None), key_attr == lookup_model.sf_id
                ).update({key_attr: lookup_model.id}, synchronize_session=False)
            except NotImplementedError:
                # Some databases such as sqlite don't support multitable update
                mappings = []
                for row, lookup_id in self.session.query(model, lookup_model.id).join(
                    lookup_model, key_attr == lookup_model.sf_id
                ):
                    mappings.append({"id": row.id, key_field: lookup_id})
                self.session.bulk_update_mappings(model, mappings)
        self.session.commit()

    def _create_tables(self):
        """Create a table for each mapping step."""
        for mapping in self.mapping.values():
            self._create_table(mapping)
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

        if not mapping.get_oid_as_pk():
            # If multiple mappings point to the same table, don't recreate the table
            if mapping.get_sf_id_table() not in self.models:
                sf_id_model_name = f"{mapping.get_sf_id_table()}Model"
                self.models[mapping.get_sf_id_table()] = type(
                    sf_id_model_name, (object,), {}
                )
                sf_id_fields = [
                    Column("id", Integer(), primary_key=True, autoincrement=True),
                    Column("sf_id", Unicode(24)),
                ]
                id_t = Table(mapping.get_sf_id_table(), self.metadata, *sf_id_fields)
                mapper(self.models[mapping.get_sf_id_table()], id_t)

        mapper(self.models[mapping.table], t, **mapper_kwargs)

    def _sqlite_dump(self):
        """Write a SQLite script output file."""
        path = self.options["sql_path"]
        with open(path, "w", encoding="utf-8") as f:
            for line in self.session.connection().connection.iterdump():
                f.write(line + "\n")

    def append_filter_clause(self, soql, filter_clause):
        """Function that applies filter clause to soql if it is defined in mapping yml file"""

        if not filter_clause:
            return soql

        # If WHERE keyword is specified in the maping file replace it with empty string.
        # match WHERE keyword only at the start of the string and whitespace after it.
        filter_clause = re.sub(
            pattern=r"^WHERE\s+",
            repl="",
            string=filter_clause.strip(),
            flags=re.IGNORECASE,
        )

        # If WHERE keyword is already in soql query(because of record type filter) add AND clause
        if " WHERE " in soql:
            soql = f"{soql} AND {filter_clause}"
        else:
            soql = f"{soql} WHERE {filter_clause}"

        return soql
