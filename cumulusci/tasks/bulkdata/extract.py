import tempfile
import unicodecsv

from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy.orm import create_session, mapper
from sqlalchemy.ext.automap import automap_base
import yaml

from cumulusci.tasks.bulkdata.utils import (
    BulkJobTaskMixin,
    download_file,
    process_incoming_rows,
    get_lookup_key_field,
    create_table,
    fields_for_mapping,
)
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import log_progress, os_friendly_path
from salesforce_bulk.util import IteratorBytesIO


class ExtractData(BulkJobTaskMixin, BaseSalesforceApiTask):
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

        for mapping in self.mappings.values():
            soql = self._soql_for_mapping(mapping)
            self._run_query(soql, mapping)

        self._drop_sf_id_columns()

        if self.options.get("sql_path"):
            self._sqlite_dump()

    def _init_db(self):
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
        with open(self.options["mapping"], "r") as f:
            self.mappings = yaml.safe_load(f)

    def _soql_for_mapping(self, mapping):
        sf_object = mapping["sf_object"]
        fields = []
        if not mapping["oid_as_pk"]:
            fields.append("Id")
        fields += [field["sf"] for field in fields_for_mapping(mapping)]
        field_list = ", ".join(fields)
        soql = f"SELECT {field_list} FROM {sf_object}"
        if "record_type" in mapping:
            soql += f" WHERE RecordType.DeveloperName = '{mapping['record_type']}'"
        return soql

    def _run_query(self, soql, mapping):
        self.logger.info(f"Creating bulk job for: {mapping['sf_object']}")
        job = self.bulk.create_query_job(mapping["sf_object"], contentType="CSV")
        self.logger.info(f"Job id: {job}")
        self.logger.info(f"Submitting query: {soql}")
        batch = self.bulk.query(job, soql)
        self.logger.info(f"Batch id: {batch}")
        self.bulk.wait_for_batch(job, batch)
        self.logger.info(f"Batch {batch} finished")
        self.bulk.close_job(job)
        self.logger.info(f"Job {job} closed")

        conn = self.session.connection()
        for result_file in self._get_results(batch, job):
            self._import_results(mapping, result_file, conn)

    def _get_results(self, batch_id, job_id):
        result_ids = self.bulk.get_query_batch_result_ids(batch_id, job_id=job_id)
        for result_id in result_ids:
            self.logger.info(f"Result id: {result_id}")
            uri = (
                f"{self.bulk.endpoint}/job/{job_id}/batch/{batch_id}/result/{result_id}"
            )
            with download_file(uri, self.bulk) as f:
                self.logger.info(f"Result {result_id} downloaded")
                yield f

    def _import_results(self, mapping, result_file, conn):
        # Map SF field names to local db column names
        sf_header = [
            name.strip('"')
            for name in result_file.readline().strip().decode("utf-8").split(",")
        ]
        columns = []
        lookup_keys = []
        for sf in sf_header:
            if sf == "Records not found for this query":
                return
            if sf:
                column = mapping.get("fields", {}).get(sf)
                if not column:
                    lookup = mapping.get("lookups", {}).get(sf, {})
                    if lookup:
                        lookup_keys.append(sf)
                        column = get_lookup_key_field(lookup, sf)
                if column:
                    columns.append(column)
        if not columns:
            return
        record_type = mapping.get("record_type")
        if record_type:
            columns.append("record_type")

        processor = log_progress(
            process_incoming_rows(result_file, record_type), self.logger
        )
        data_file = IteratorBytesIO(processor)
        if mapping["oid_as_pk"]:
            self._sql_bulk_insert_from_csv(conn, mapping["table"], columns, data_file)
        else:
            # If using the autogenerated id field, split out the CSV file from the Bulk API
            # into two separate files and load into the main table and the sf_id_table
            with tempfile.TemporaryFile("w+b") as f_values:
                with tempfile.TemporaryFile("w+b") as f_ids:
                    data_file_values, data_file_ids = self._split_batch_csv(
                        data_file, f_values, f_ids
                    )
                    self._sql_bulk_insert_from_csv(
                        conn, mapping["table"], columns, data_file_values
                    )
                    self._sql_bulk_insert_from_csv(
                        conn, mapping["sf_id_table"], ["sf_id"], data_file_ids
                    )

        if "RecordTypeId" in mapping["fields"]:
            self._extract_record_types(
                mapping["sf_object"], mapping["record_type_table"], conn
            )

        self.session.commit()

        if lookup_keys and not mapping["oid_as_pk"]:
            self._convert_lookups_to_id(mapping, lookup_keys)

    def _get_mapping_for_table(self, table):
        """ Returns the first mapping for a table name """
        for mapping in self.mappings.values():
            if mapping["table"] == table:
                return mapping

    def _split_batch_csv(self, data_file, f_values, f_ids):
        writer_values = unicodecsv.writer(f_values)
        writer_ids = unicodecsv.writer(f_ids)
        for row in unicodecsv.reader(data_file):
            writer_values.writerow(row[1:])
            writer_ids.writerow(row[:1])
        f_values.seek(0)
        f_ids.seek(0)
        return f_values, f_ids

    def _convert_lookups_to_id(self, mapping, lookup_keys):
        for lookup_key in lookup_keys:
            lookup_dict = mapping["lookups"][lookup_key]
            model = self.models[mapping["table"]]
            lookup_mapping = self._get_mapping_for_table(lookup_dict["table"])
            lookup_model = self.models[lookup_mapping["sf_id_table"]]
            key_field = get_lookup_key_field(lookup_dict, lookup_key)
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
        for mapping in self.mappings.values():
            self._create_table(mapping)
        self.metadata.create_all()

    def _create_table(self, mapping):
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
        for mapping in self.mappings.values():
            if mapping.get("oid_as_pk"):
                continue
            self.metadata.tables[mapping["sf_id_table"]].drop()

    def _sqlite_dump(self):
        path = self.options["sql_path"]
        with open(path, "w") as f:
            for line in self.session.connection().connection.iterdump():
                f.write(line + "\n")
