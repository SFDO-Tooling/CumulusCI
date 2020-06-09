import csv
from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy.orm import create_session, mapper
from sqlalchemy.ext.automap import automap_base
import tempfile

from cumulusci.core.exceptions import TaskOptionsError, BulkDataException
from cumulusci.tasks.bulkdata.utils import (
    SqlAlchemyMixin,
    create_table,
    fields_for_mapping,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.bulkdata.step import BulkApiQueryOperation, DataOperationStatus
from cumulusci.utils import os_friendly_path, log_progress
from cumulusci.tasks.bulkdata.mapping_parser import parse_from_yaml


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
    }

    def _init_options(self, kwargs):
        super(ExtractData, self)._init_options(kwargs)
        if self.options.get("database_url"):
            # prefer database_url if it's set
            self.options["sql_path"] = None
        elif self.options.get("sql_path"):
            self.logger.info("Using in-memory sqlite database")
            self.options["database_url"] = "sqlite://"
            self.options["sql_path"] = os_friendly_path(self.options["sql_path"])
        else:
            raise TaskOptionsError(
                "You must set either the database_url or sql_path option."
            )

    def _run_task(self):
        self._init_mapping()
        self._init_db()

        for mapping in self.mapping.values():
            soql = self._soql_for_mapping(mapping)
            self._run_query(soql, mapping)

        self._drop_sf_id_columns()

        if self.options.get("sql_path"):
            self._sqlite_dump()

    def _init_db(self):
        """Initialize the database and automapper."""
        self.models = {}

        # initialize the DB engine
        self.engine = create_engine(self.options["database_url"])

        # initialize DB metadata
        self.metadata = MetaData()
        self.metadata.bind = self.engine

        # Create the tables
        self._create_tables()

        # initialize the automap mapping
        self.base = automap_base(bind=self.engine, metadata=self.metadata)
        self.base.prepare(self.engine, reflect=True)

        # initialize session
        self.session = create_session(bind=self.engine, autocommit=False)

    def _init_mapping(self):
        """Load a YAML mapping file."""
        mapping_file_path = self.options["mapping"]
        if not mapping_file_path:
            raise TaskOptionsError("Mapping file path required")

        self.mapping = parse_from_yaml(mapping_file_path)

    def _fields_for_mapping(self, mapping):
        """Return a flat list of fields for this mapping."""
        fields = []
        if not mapping["oid_as_pk"]:
            fields.append("Id")
        fields += [field["sf"] for field in fields_for_mapping(mapping)]

        return fields

    def _soql_for_mapping(self, mapping):
        """Return a SOQL query suitable for extracting data for this mapping."""
        sf_object = mapping["sf_object"]
        fields = self._fields_for_mapping(mapping)
        soql = f"SELECT {', '.join(fields)} FROM {sf_object}"
        if mapping.record_type:
            soql += f" WHERE RecordType.DeveloperName = '{mapping.record_type}'"

        return soql

    def _run_query(self, soql, mapping):
        """Execute a Bulk API query job and store the results."""
        step = BulkApiQueryOperation(
            sobject=mapping["sf_object"], api_options={}, context=self, query=soql
        )
        self.logger.info(f"Extracting data for sObject {mapping['sf_object']}")
        step.query()

        if step.job_result.status is DataOperationStatus.SUCCESS:
            if step.job_result.records_processed:
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
        fields = self._fields_for_mapping(mapping)
        columns = []
        lookup_keys = []
        for field_name in fields:
            column = mapping.get("fields", {}).get(field_name)
            if not column:
                lookup = mapping.get("lookups", {}).get(field_name, {})
                if lookup:
                    lookup_keys.append(field_name)
                    column = lookup.get_lookup_key_field()
            if column:
                columns.append(column)

        if not columns:
            return
        record_type = mapping.get("record_type")
        if record_type:
            columns.append("record_type")

        # FIXME: log_progress needs to know our batch size, when made configurable.
        record_iterator = log_progress(step.get_results(), self.logger)
        if record_type:
            record_iterator = (record + [record_type] for record in record_iterator)

        if mapping["oid_as_pk"]:
            self._sql_bulk_insert_from_records(
                connection=conn,
                table=mapping["table"],
                columns=columns,
                record_iterable=record_iterator,
            )
        else:
            # If using the autogenerated id field, split out the returned records
            # into two separate files and load into the main table and the sf_id_table

            with tempfile.TemporaryFile("w+", newline="") as f_values:
                with tempfile.TemporaryFile("w+", newline="") as f_ids:
                    data_file_values, data_file_ids = self._split_batch_csv(
                        record_iterator, f_values, f_ids
                    )
                    self._sql_bulk_insert_from_records(
                        connection=conn,
                        table=mapping["table"],
                        columns=columns,
                        record_iterable=csv.reader(data_file_values),
                    )
                    self._sql_bulk_insert_from_records(
                        connection=conn,
                        table=mapping["sf_id_table"],
                        columns=["sf_id"],
                        record_iterable=csv.reader(data_file_ids),
                    )

        if "RecordTypeId" in mapping["fields"]:
            self._extract_record_types(
                mapping["sf_object"], mapping["record_type_table"], conn
            )

        self.session.commit()

        if lookup_keys and not mapping["oid_as_pk"]:
            self._convert_lookups_to_id(mapping, lookup_keys)

    def _get_mapping_for_table(self, table):
        """Return the first mapping for a table name """
        for mapping in self.mapping.values():
            if mapping["table"] == table:
                return mapping

    def _split_batch_csv(self, records, f_values, f_ids):
        """Split the record generator and return two files,
        one containing Ids only and the other record data."""
        writer_values = csv.writer(f_values)
        writer_ids = csv.writer(f_ids)
        for row in records:
            writer_values.writerow(row[1:])
            writer_ids.writerow(row[:1])
        f_values.seek(0)
        f_ids.seek(0)
        return f_values, f_ids

    def _convert_lookups_to_id(self, mapping, lookup_keys):
        """Rewrite persisted Salesforce Ids to refer to auto-PKs."""
        for lookup_key in lookup_keys:
            lookup_info = mapping["lookups"][lookup_key]
            model = self.models[mapping["table"]]
            lookup_mapping = self._get_mapping_for_table(lookup_info["table"])
            lookup_model = self.models[lookup_mapping["sf_id_table"]]
            key_field = lookup_info.get_lookup_key_field()
            key_attr = getattr(model, key_field)
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
        model_name = f"{mapping['table']}Model"
        mapper_kwargs = {}
        self.models[mapping["table"]] = type(model_name, (object,), {})

        t = create_table(mapping, self.metadata)

        if "RecordTypeId" in mapping["fields"]:
            # We're using Record Type Mapping support.
            mapping["record_type_table"] = mapping["sf_object"] + "_rt_mapping"
            # If multiple mappings point to the same table, don't recreate the table
            if mapping["record_type_table"] not in self.models:
                self._create_record_type_table(mapping["record_type_table"])

        if not mapping["oid_as_pk"]:
            mapping["sf_id_table"] = mapping["table"] + "_sf_id"
            # If multiple mappings point to the same table, don't recreate the table
            if mapping["sf_id_table"] not in self.models:
                sf_id_model_name = f"{mapping['sf_id_table']}Model"
                self.models[mapping["sf_id_table"]] = type(
                    sf_id_model_name, (object,), {}
                )
                sf_id_fields = [
                    Column("id", Integer(), primary_key=True, autoincrement=True),
                    Column("sf_id", Unicode(24)),
                ]
                id_t = Table(mapping["sf_id_table"], self.metadata, *sf_id_fields)
                mapper(self.models[mapping["sf_id_table"]], id_t)

        mapper(self.models[mapping["table"]], t, **mapper_kwargs)

    def _drop_sf_id_columns(self):
        """Drop Salesforce Id storage tables after rewriting Ids to auto-PKs."""
        for mapping in self.mapping.values():
            if mapping.get("oid_as_pk"):
                continue
            self.metadata.tables[mapping["sf_id_table"]].drop()

    def _sqlite_dump(self):
        """Write a SQLite script output file."""
        path = self.options["sql_path"]
        with open(path, "w") as f:
            for line in self.session.connection().connection.iterdump():
                f.write(line + "\n")
