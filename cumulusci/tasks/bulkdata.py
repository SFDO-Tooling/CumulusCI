from future import standard_library

standard_library.install_aliases()
from builtins import zip
from collections import defaultdict
from collections import OrderedDict
from contextlib import contextmanager
import datetime
import io
import os
import time
import tempfile
import xml.etree.ElementTree as ET

from salesforce_bulk.util import IteratorBytesIO
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import aliased
from sqlalchemy.orm import create_session
from sqlalchemy.orm import mapper
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy import text
from sqlalchemy import types
from sqlalchemy import event
import requests
import unicodecsv

from cumulusci.core.utils import (
    process_bool_arg,
    process_list_arg,
    ordered_yaml_load,
    ordered_yaml_dump,
)
from cumulusci.core.exceptions import BulkDataException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import convert_to_snake_case, log_progress, os_friendly_path

# TODO: UserID Catcher
# TODO: Dater


# Create a custom sqlalchemy field type for sqlite datetime fields which are stored as integer of epoch time
class EpochType(types.TypeDecorator):
    impl = types.Integer

    epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)

    def process_bind_param(self, value, dialect):
        return int((value - self.epoch).total_seconds()) * 1000

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.epoch + datetime.timedelta(seconds=value / 1000)


# Listen for sqlalchemy column_reflect event and map datetime fields to EpochType
@event.listens_for(Table, "column_reflect")
def setup_epoch(inspector, table, column_info):
    if isinstance(column_info["type"], types.DateTime):
        column_info["type"] = EpochType()


class BulkJobTaskMixin(object):
    def _job_state_from_batches(self, job_id):
        uri = "{}/job/{}/batch".format(self.bulk.endpoint, job_id)
        response = requests.get(uri, headers=self.bulk.headers())
        return self._parse_job_state(response.content)

    def _parse_job_state(self, xml):
        tree = ET.fromstring(xml)
        statuses = [el.text for el in tree.iterfind(".//{%s}state" % self.bulk.jobNS)]
        state_messages = [
            el.text for el in tree.iterfind(".//{%s}stateMessage" % self.bulk.jobNS)
        ]

        if "Not Processed" in statuses:
            return "Aborted", None
        elif "InProgress" in statuses or "Queued" in statuses:
            return "InProgress", None
        elif "Failed" in statuses:
            return "Failed", state_messages

        return "Completed", None

    def _wait_for_job(self, job_id):
        while True:
            job_status = self.bulk.job_status(job_id)
            self.logger.info(
                "    Waiting for job {} ({}/{})".format(
                    job_id,
                    job_status["numberBatchesCompleted"],
                    job_status["numberBatchesTotal"],
                )
            )
            result, messages = self._job_state_from_batches(job_id)
            if result != "InProgress":
                break
            time.sleep(10)
        self.logger.info("Job {} finished with result: {}".format(job_id, result))
        if result == "Failed":
            for state_message in messages:
                self.logger.error("Batch failure message: {}".format(state_message))

        return result

    def _sql_bulk_insert_from_csv(self, conn, table, columns, data_file):
        if conn.dialect.name in ("postgresql", "psycopg2"):
            # psycopg2 (the postgres driver) supports COPY FROM
            # to efficiently bulk insert rows in CSV format
            with conn.connection.cursor() as cursor:
                cursor.copy_expert(
                    "COPY {} ({}) FROM STDIN WITH (FORMAT CSV)".format(
                        table, ",".join(columns)
                    ),
                    data_file,
                )
        else:
            # For other db drivers we need to use standard SQL
            # -- this is optimized for ease of implementation
            # rather than performance and may need more work.
            reader = unicodecsv.DictReader(data_file, columns)
            table = self.metadata.tables[table]
            rows = list(reader)
            if rows:
                conn.execute(table.insert().values(rows))
        self.session.flush()


class DeleteData(BaseSalesforceApiTask, BulkJobTaskMixin):

    task_options = {
        "objects": {
            "description": "A list of objects to delete records from in order of deletion.  If passed via command line, use a comma separated string",
            "required": True,
        },
        "hardDelete": {
            "description": "If True, perform a hard delete, bypassing the recycle bin. Default: False"
        },
    }

    def _init_options(self, kwargs):
        super(DeleteData, self)._init_options(kwargs)

        # Split and trim objects string into a list if not already a list
        self.options["objects"] = process_list_arg(self.options["objects"])
        self.options["hardDelete"] = process_bool_arg(self.options.get("hardDelete"))

    def _run_task(self):
        for obj in self.options["objects"]:
            self.logger.info("Deleting all {} records".format(obj))
            delete_job = self._create_job(obj)
            if delete_job is not None:
                self._wait_for_job(delete_job)

    def _create_job(self, obj):
        # Query for rows to delete
        delete_rows = self._query_salesforce_for_records_to_delete(obj)
        if not delete_rows:
            self.logger.info("  No {} objects found, skipping delete".format(obj))
            return

        # Upload all the batches
        operation = "hardDelete" if self.options["hardDelete"] else "delete"
        delete_job = self.bulk.create_job(obj, operation)
        self.logger.info("  Deleting {} {} records".format(len(delete_rows), obj))
        batch_num = 1
        for batch in self._upload_batches(delete_job, delete_rows):
            self.logger.info("    Uploaded batch {}".format(batch))
            batch_num += 1
        self.bulk.close_job(delete_job)
        return delete_job

    def _query_salesforce_for_records_to_delete(self, obj):
        # Query for all record ids
        self.logger.info("  Querying for all {} objects".format(obj))
        query_job = self.bulk.create_query_job(obj, contentType="CSV")
        batch = self.bulk.query(query_job, "select Id from {}".format(obj))
        while not self.bulk.is_batch_done(batch, query_job):
            time.sleep(10)
        self.bulk.close_job(query_job)
        delete_rows = []
        for result in self.bulk.get_all_results_for_query_batch(batch, query_job):
            reader = unicodecsv.DictReader(result, encoding="utf-8")
            for row in reader:
                delete_rows.append(row)
        return delete_rows

    def _split_batches(self, data, batch_size):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(data), batch_size):
            yield data[i : i + batch_size]

    def _upload_batches(self, job, data):
        uri = "{}/job/{}/batch".format(self.bulk.endpoint, job)
        headers = self.bulk.headers({"Content-Type": "text/csv"})
        for batch in self._split_batches(data, 10000):
            rows = ['"Id"']
            rows += ['"{}"'.format(record["Id"]) for record in batch]
            resp = requests.post(uri, data="\n".join(rows), headers=headers)
            content = resp.content
            if resp.status_code >= 400:
                self.bulk.raise_error(content, resp.status_code)

            tree = ET.fromstring(content)
            batch_id = tree.findtext("{%s}id" % self.bulk.jobNS)

            yield batch_id


class LoadData(BulkJobTaskMixin, BaseSalesforceApiTask):

    task_options = {
        "database_url": {
            "description": "The database url to a database containing the test data to load",
            "required": True,
        },
        "mapping": {
            "description": "The path to a yaml file containing mappings of the database fields to Salesforce object fields",
            "required": True,
        },
        "start_step": {
            "description": "If specified, skip steps before this one in the mapping",
            "required": False,
        },
        "sql_path": {
            "description": "If specified, a database will be created from an SQL script at the provided path"
        },
        "ignore_row_errors": {
            "description": "If True, allow the load to continue even if individual rows fail to load."
        },
    }

    def _init_options(self, kwargs):
        super(LoadData, self)._init_options(kwargs)

        self.options["ignore_row_errors"] = process_bool_arg(
            self.options.get("ignore_row_errors", False)
        )
        if self.options.get("sql_path"):
            if self.options.get("database_url"):
                raise TaskOptionsError(
                    "The database_url option is set dynamically with the sql_path option.  Please unset the database_url option."
                )
            self.options["sql_path"] = os_friendly_path(self.options["sql_path"])
            if not os.path.isfile(self.options["sql_path"]):
                raise TaskOptionsError(
                    "File {} does not exist".format(self.options["sql_path"])
                )
            self.logger.info("Using in-memory sqlite database")
            self.options["database_url"] = "sqlite://"

    def _run_task(self):
        self._init_mapping()
        self._init_db()

        start_step = self.options.get("start_step")
        started = False
        for name, mapping in self.mapping.items():
            # Skip steps until start_step
            if not started and start_step and name != start_step:
                self.logger.info("Skipping step: {}".format(name))
                continue
            started = True

            self.logger.info("Running Job: {}".format(name))
            result = self._load_mapping(mapping)
            if result != "Completed":
                raise BulkDataException(
                    "Job {} did not complete successfully".format(name)
                )

    def _load_mapping(self, mapping):
        """Load data for a single step."""
        mapping["oid_as_pk"] = bool(mapping.get("fields", {}).get("Id"))
        job_id, local_ids_for_batch = self._create_job(mapping)
        result = self._wait_for_job(job_id)

        self._store_inserted_ids(mapping, job_id, local_ids_for_batch)
        return result

    def _create_job(self, mapping):
        """Initiate a bulk insert and upload batches to run in parallel."""
        job_id = self.bulk.create_insert_job(mapping["sf_object"], contentType="CSV")
        self.logger.info("  Created bulk job {}".format(job_id))

        # Upload batches
        local_ids_for_batch = {}
        for batch_file, local_ids in self._get_batches(mapping):
            batch_id = self.bulk.post_batch(job_id, batch_file)
            local_ids_for_batch[batch_id] = local_ids
            self.logger.info("    Uploaded batch {}".format(batch_id))

        self.bulk.close_job(job_id)
        return job_id, local_ids_for_batch

    def _get_batches(self, mapping, batch_size=10000):
        """Get data from the local db"""
        action = mapping.get("action", "insert")
        fields = mapping.get("fields", {}).copy()
        static = mapping.get("static", {})
        lookups = mapping.get("lookups", {})
        record_type = mapping.get("record_type")

        # Skip Id field on insert
        if action == "insert" and "Id" in fields:
            del fields["Id"]

        # Build the list of fields to import
        columns = []
        columns.extend(fields.keys())
        columns.extend(lookups.keys())
        columns.extend(static.keys())

        if record_type:
            columns.append("RecordTypeId")
            # default to the profile assigned recordtype if we can't find any
            # query for the RT by developer name
            query = (
                "SELECT Id FROM RecordType WHERE SObjectType='{0}'"
                "AND DeveloperName = '{1}' LIMIT 1"
            )
            record_type_id = self.sf.query(
                query.format(mapping.get("sf_object"), record_type)
            )["records"][0]["Id"]

        query = self._query_db(mapping)

        total_rows = 0
        batch_num = 1

        def start_batch():
            batch_file = io.BytesIO()
            writer = unicodecsv.writer(batch_file)
            writer.writerow(columns)
            batch_ids = []
            return batch_file, writer, batch_ids

        batch_file, writer, batch_ids = start_batch()
        for row in query.yield_per(batch_size):
            total_rows += 1

            # Add static values to row
            pkey = row[0]
            row = list(row[1:]) + list(static.values())
            if record_type:
                row.append(record_type_id)

            writer.writerow([self._convert(value) for value in row])
            batch_ids.append(pkey)

            # Yield and start a new file every [batch_size] rows
            if not total_rows % batch_size:
                batch_file.seek(0)
                self.logger.info("    Processing batch {}".format(batch_num))
                yield batch_file, batch_ids
                batch_file, writer, batch_ids = start_batch()
                batch_num += 1

        # Yield result file for final batch
        if batch_ids:
            batch_file.seek(0)
            yield batch_file, batch_ids

        self.logger.info(
            "  Prepared {} rows for import to {}".format(
                total_rows, mapping["sf_object"]
            )
        )

    def _query_db(self, mapping):
        """Build a query to retrieve data from the local db.

        Includes columns from the mapping
        as well as joining to the id tables to get real SF ids
        for lookups.
        """
        model = self.models[mapping.get("table")]

        # Use primary key instead of the field mapped to SF Id
        fields = mapping.get("fields", {}).copy()
        if mapping["oid_as_pk"]:
            del fields["Id"]
        id_column = model.__table__.primary_key.columns.keys()[0]
        columns = [getattr(model, id_column)]

        for f in fields.values():
            columns.append(model.__table__.columns[f])
        lookups = mapping.get("lookups", {}).copy()
        for lookup in lookups.values():
            lookup["aliased_table"] = aliased(
                self.metadata.tables["{}_sf_ids".format(lookup["table"])]
            )
            columns.append(lookup["aliased_table"].columns.sf_id)

        query = self.session.query(*columns)
        if "record_type" in mapping and hasattr(model, "record_type"):
            query = query.filter(model.record_type == mapping["record_type"])
        if "filters" in mapping:
            filter_args = []
            for f in mapping["filters"]:
                filter_args.append(text(f))
            query = query.filter(*filter_args)
        for sf_field, lookup in lookups.items():
            # Outer join with lookup ids table:
            # returns main obj even if lookup is null
            key_field = get_lookup_key_field(lookup, sf_field)
            value_column = getattr(model, key_field)
            query = query.outerjoin(
                lookup["aliased_table"],
                lookup["aliased_table"].columns.id == value_column,
            )
            # Order by foreign key to minimize lock contention
            # by trying to keep lookup targets in the same batch
            lookup_column = getattr(model, key_field)
            query = query.order_by(lookup_column)
        self.logger.info(str(query))
        return query

    def _convert(self, value):
        if value:
            if isinstance(value, datetime.datetime):
                return value.isoformat()
            return value

    def _store_inserted_ids(self, mapping, job_id, local_ids_for_batch):
        """Get the job results and store inserted SF Ids in a new table"""
        id_table_name = self._reset_id_table(mapping)
        conn = self.session.connection()
        for batch_id, local_ids in local_ids_for_batch.items():
            try:
                results_url = "{}/job/{}/batch/{}/result".format(
                    self.bulk.endpoint, job_id, batch_id
                )
                # Download entire result file to a temporary file first
                # to avoid the server dropping connections
                with _download_file(results_url, self.bulk) as f:
                    self.logger.info(
                        "  Downloaded results for batch {}".format(batch_id)
                    )
                    self._store_inserted_ids_for_batch(
                        f, local_ids, id_table_name, conn
                    )
                self.logger.info(
                    "  Updated {} for batch {}".format(id_table_name, batch_id)
                )
            except BulkDataException:
                raise
            except Exception as e:
                raise BulkDataException(
                    "Failed to download results for batch {} ({})".format(
                        batch_id, str(e)
                    )
                )

        self.session.commit()

    def _reset_id_table(self, mapping):
        """Create an empty table to hold the inserted SF Ids"""
        if not hasattr(self, "_initialized_id_tables"):
            self._initialized_id_tables = set()
        id_table_name = "{}_sf_ids".format(mapping["table"])
        if id_table_name not in self._initialized_id_tables:
            if id_table_name in self.metadata.tables:
                self.metadata.remove(self.metadata.tables[id_table_name])
            id_table = Table(
                id_table_name,
                self.metadata,
                Column("id", Unicode(255), primary_key=True),
                Column("sf_id", Unicode(18)),
            )
            if id_table.exists():
                id_table.drop()
            id_table.create()
            self._initialized_id_tables.add(id_table_name)
        return id_table_name

    def _store_inserted_ids_for_batch(
        self, result_file, local_ids, id_table_name, conn
    ):
        # Set up a function to generate rows based on this result file
        def produce_csv():
            """Iterate over job results and prepare rows for id table"""
            reader = unicodecsv.reader(result_file)
            next(reader)  # skip header
            i = 0
            for row, local_id in zip(reader, local_ids):
                if row[1] == "true":  # Success
                    sf_id = row[0]
                    yield "{},{}\n".format(local_id, sf_id).encode("utf-8")
                else:
                    if self.options["ignore_row_errors"]:
                        self.logger.warning(
                            "      Error on row {}: {}".format(i, row[3])
                        )
                    else:
                        raise BulkDataException("Error on row {}: {}".format(i, row[3]))
                i += 1

        # Bulk insert rows into id table
        columns = ("id", "sf_id")
        data_file = IteratorBytesIO(produce_csv())
        self._sql_bulk_insert_from_csv(conn, id_table_name, columns, data_file)

    def _sqlite_load(self):
        conn = self.session.connection()
        cursor = conn.connection.cursor()
        with open(self.options["sql_path"], "r") as f:
            try:
                cursor.executescript(f.read())
            finally:
                cursor.close()
        # self.session.flush()

    def _init_db(self):
        # initialize the DB engine
        self.engine = create_engine(self.options["database_url"])

        # initialize the DB session
        self.session = Session(self.engine)

        if self.options.get("sql_path"):
            self._sqlite_load()

        # initialize DB metadata
        self.metadata = MetaData()
        self.metadata.bind = self.engine

        # initialize the automap mapping
        self.base = automap_base(bind=self.engine, metadata=self.metadata)
        self.base.prepare(self.engine, reflect=True)

        # Loop through mappings and reflect each referenced table
        self.models = {}
        for name, mapping in self.mapping.items():
            if "table" in mapping and mapping["table"] not in self.models:
                self.models[mapping["table"]] = self.base.classes[mapping["table"]]

    def _init_mapping(self):
        with open(self.options["mapping"], "r") as f:
            self.mapping = ordered_yaml_load(f)


class ExtractData(BulkJobTaskMixin, BaseSalesforceApiTask):
    task_options = {
        "database_url": {
            "description": "A DATABASE_URL where the query output should be written",
            "required": True,
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
        if self.options.get("sql_path"):
            if self.options.get("database_url"):
                raise TaskOptionsError(
                    "The database_url option is set dynamically with the sql_path option.  Please unset the database_url option."
                )
            self.logger.info("Using in-memory sqlite database")
            self.options["database_url"] = "sqlite://"
            self.options["sql_path"] = os_friendly_path(self.options["sql_path"])

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
            self.mappings = ordered_yaml_load(f)

    def _soql_for_mapping(self, mapping):
        sf_object = mapping["sf_object"]
        fields = []
        if not mapping["oid_as_pk"]:
            fields.append("Id")
        fields += [field["sf"] for field in self._fields_for_mapping(mapping)]
        soql = "SELECT {fields} FROM {sf_object}".format(
            **{"fields": ", ".join(fields), "sf_object": sf_object}
        )
        if "record_type" in mapping:
            soql += " WHERE RecordType.DeveloperName = '{}'".format(
                mapping["record_type"]
            )
        return soql

    def _run_query(self, soql, mapping):
        self.logger.info("Creating bulk job for: {sf_object}".format(**mapping))
        job = self.bulk.create_query_job(mapping["sf_object"], contentType="CSV")
        self.logger.info("Job id: {0}".format(job))
        self.logger.info("Submitting query: {}".format(soql))
        batch = self.bulk.query(job, soql)
        self.logger.info("Batch id: {0}".format(batch))
        self.bulk.wait_for_batch(job, batch)
        self.logger.info("Batch {0} finished".format(batch))
        self.bulk.close_job(job)
        self.logger.info("Job {0} closed".format(job))

        conn = self.session.connection()
        for result_file in self._get_results(batch, job):
            self._import_results(mapping, result_file, conn)

    def _get_results(self, batch_id, job_id):
        result_ids = self.bulk.get_query_batch_result_ids(batch_id, job_id=job_id)
        for result_id in result_ids:
            self.logger.info("Result id: {}".format(result_id))
            uri = "{}/job/{}/batch/{}/result/{}".format(
                self.bulk.endpoint, job_id, batch_id, result_id
            )
            with _download_file(uri, self.bulk) as f:
                self.logger.info("Result {} downloaded".format(result_id))
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
            writer_ids.writerow([row[:1]])
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
        model_name = "{}Model".format(mapping["table"])
        mapper_kwargs = {}
        table_kwargs = {}
        self.models[mapping["table"]] = type(model_name, (object,), {})

        # Provide support for legacy mappings which used the OID as the pk but
        # default to using an autoincrementing int pk and a separate sf_id column
        fields = []
        mapping["oid_as_pk"] = bool(mapping.get("fields", {}).get("Id"))
        if mapping["oid_as_pk"]:
            id_column = mapping["fields"]["Id"]
            fields.append(Column(id_column, Unicode(255), primary_key=True))
        else:
            fields.append(Column("id", Integer(), primary_key=True, autoincrement=True))
        for field in self._fields_for_mapping(mapping):
            if mapping["oid_as_pk"] and field["sf"] == "Id":
                continue
            fields.append(Column(field["db"], Unicode(255)))
        if "record_type" in mapping:
            fields.append(Column("record_type", Unicode(255)))
        t = Table(mapping["table"], self.metadata, *fields, **table_kwargs)
        if t.exists():
            raise BulkDataException("Table already exists: {}".format(mapping["table"]))

        if not mapping["oid_as_pk"]:
            mapping["sf_id_table"] = mapping["table"] + "_sf_id"
            # If multiple mappings point to the same table, don't recreate the table
            if mapping["sf_id_table"] not in self.models:
                sf_id_model_name = "{}Model".format(mapping["sf_id_table"])
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

    def _fields_for_mapping(self, mapping):
        fields = []
        for sf_field, db_field in mapping.get("fields", {}).items():
            fields.append({"sf": sf_field, "db": db_field})
        for sf_field, lookup in mapping.get("lookups", {}).items():
            fields.append(
                {"sf": sf_field, "db": get_lookup_key_field(lookup, sf_field)}
            )
        return fields

    def _drop_sf_id_columns(self):
        for mapping in self.mappings.values():
            if mapping.get("oid_as_pk"):
                continue
            self.metadata.tables[mapping["sf_id_table"]].drop()

    def _sqlite_dump(self):
        path = self.options["sql_path"]
        if os.path.exists(path):
            os.remove(path)
        with open(path, "w") as f:
            for line in self.session.connection().connection.iterdump():
                f.write(line + "\n")


class GenerateMapping(BaseSalesforceApiTask):
    task_docs = """
    Generate a mapping file for use with the `extract_dataset` and `load_dataset` tasks.
    This task will examine the schema in the specified org and attempt to infer a
    mapping suitable for extracting data in packaged and custom objects as well as
    customized standard objects.

    Mappings cannot include reference cycles - situations where Object A refers to B,
    and B also refers to A. Mapping generation will fail for such data models; to
    resolve the issue, specify the `ignore` option with the name of one of the
    involved lookup fields to suppress it. `ignore` can be specified as a list in
    `cumulusci.yml` or as a comma-separated string at the command line.

    In most cases, the mapping generated will need minor tweaking by the user. Note
    that the mapping omits features that are not currently well supported by the
    `extract_dataset` and `load_dataset` tasks, including self-lookups and references to
    the `User` object.
    """

    task_options = {
        "path": {"description": "Location to write the mapping file", "required": True},
        "namespace_prefix": {"description": "The namespace prefix to use"},
        "ignore": {
            "description": "Object API names, or fields in Object.Field format, to ignore"
        },
    }

    core_fields = ["Id", "Name", "FirstName", "LastName"]

    def _init_options(self, kwargs):
        super(GenerateMapping, self)._init_options(kwargs)
        if "namespace_prefix" not in self.options:
            self.options["namespace_prefix"] = ""

        if self.options["namespace_prefix"] and not self.options[
            "namespace_prefix"
        ].endswith("__"):
            self.options["namespace_prefix"] += "__"

        self.options["ignore"] = process_list_arg(self.options.get("ignore", []))

    def _run_task(self):
        self.logger.info("Collecting sObject information")
        self._collect_objects()
        self._build_schema()
        self.logger.info("Creating mapping schema")
        self._build_mapping()
        with open(self.options["path"], "w") as f:
            ordered_yaml_dump(self.mapping, f)

    def _collect_objects(self):
        """Walk the global describe and identify the sObjects we need to include in a minimal operation."""
        self.mapping_objects = []

        # Cache the global describe, which we'll walk.
        self.global_describe = self.sf.describe()

        # First, we'll get a list of all objects that are either
        # (a) custom, no namespace
        # (b) custom, with our namespace
        # (c) not ours (standard or other package), but have fields with our namespace or no namespace
        self.describes = {}  # Cache per-object describes for efficiency
        for obj in self.global_describe["sobjects"]:
            self.describes[obj["name"]] = getattr(self.sf, obj["name"]).describe()
            if self._is_our_custom_api_name(obj["name"]) or self._has_our_custom_fields(
                self.describes[obj["name"]]
            ):
                if self._is_object_mappable(obj):
                    self.mapping_objects.append(obj["name"])

        # Add any objects that are required by our own,
        # meaning any object we are looking up to with a custom field,
        # or any master-detail parent of any included object.
        index = 0
        while index < len(self.mapping_objects):
            obj = self.mapping_objects[index]
            for field in self.describes[obj]["fields"]:
                if field["type"] == "reference":
                    if field["relationshipOrder"] == 1 or self._is_any_custom_api_name(
                        field["name"]
                    ):
                        self.mapping_objects.extend(
                            [
                                obj
                                for obj in field["referenceTo"]
                                if obj not in self.mapping_objects
                                and self._is_object_mappable(self.describes[obj])
                            ]
                        )

            index += 1

    def _build_schema(self):
        """Convert self.mapping_objects into a schema, including field details and interobject references,
        in self.schema and self.refs"""

        # Now, find all the fields we need to include.
        # For custom objects, we include all custom fields. This includes custom objects
        # that our package doesn't own.
        # For standard objects, we include all custom fields, all required standard fields,
        # and master-detail relationships. Required means createable and not nillable.
        self.schema = {}
        self.refs = defaultdict(lambda: defaultdict(set))
        for obj in self.mapping_objects:
            self.schema[obj] = {}

            for field in self.describes[obj]["fields"]:
                if any(
                    [
                        self._is_any_custom_api_name(field["name"]),
                        self._is_core_field(field["name"]),
                        self._is_required_field(field),
                        self._is_lookup_to_included_object(field),
                    ]
                ):
                    if self._is_field_mappable(obj, field):
                        self.schema[obj][field["name"]] = field

                        if field["type"] == "reference":
                            for target in field["referenceTo"]:
                                # We've already vetted that this field is referencing
                                # included objects, via `_is_field_mappable()`
                                self.refs[obj][target].add(field["name"])

    def _build_mapping(self):
        """Output self.schema in mapping file format by constructing an OrderedDict and serializing to YAML"""
        objs = set(self.schema.keys())
        stack = self._split_dependencies(objs, self.refs)

        field_sort = (
            lambda f: "  " + f
            if f == "Id"
            else (" " + f if f in self.core_fields else f)
        )

        self.mapping = OrderedDict()
        for obj in stack:
            key = "Insert {}".format(obj)
            self.mapping[key] = OrderedDict()
            self.mapping[key]["sf_object"] = "{}".format(obj)
            self.mapping[key]["table"] = "{}".format(obj.lower())
            fields = []
            lookups = []
            for field in self.schema[obj].values():
                if field["type"] == "reference":
                    lookups.append(field["name"])
                else:
                    fields.append(field["name"])
            self.mapping[key]["fields"] = OrderedDict()
            if fields:
                if "Id" not in fields:
                    fields.append("Id")
                fields.sort(key=field_sort)
                for field in fields:
                    self.mapping[key]["fields"][field] = (
                        field.lower() if field != "Id" else "sf_id"
                    )
            if lookups:
                lookups.sort(key=field_sort)
                self.mapping[key]["lookups"] = OrderedDict()
                for field in lookups:
                    self.mapping[key]["lookups"][field] = {
                        "table": self.schema[obj][field]["referenceTo"][0].lower()
                    }
                    if len(self.schema[obj][field]["referenceTo"]) > 1:
                        self.logger.warning(
                            "Field {}.{} is a polymorphic lookup, which is not supported".format(
                                obj, field
                            )
                        )

    def _split_dependencies(self, objs, dependencies):
        """Attempt to flatten the object network into a sequence of load operations. May throw BulkDataException
        if reference cycles exist in the network"""
        stack = []
        objs_remaining = objs.copy()

        # The structure of `dependencies` is:
        # key = object, value = set of objects it references.

        # Iterate through our list of objects
        # For each object, if it is not dependent on any other objects, place it at the end of the stack.
        # Once an object is placed in the stack, remove dependencies to it (they're satisfied)
        while objs_remaining:
            objs_without_deps = [
                obj
                for obj in objs_remaining
                if obj not in dependencies or not dependencies[obj]
            ]

            if not objs_without_deps:
                self.logger.error(
                    "Unable to complete mapping; the schema contains reference cycles or unresolved dependencies."
                )
                self.logger.info("Mapped objects: {}".format(", ".join(stack)))
                self.logger.info("Remaining objects:")
                for obj in objs_remaining:
                    self.logger.info(obj)
                    for other_obj in dependencies[obj]:
                        self.logger.info(
                            "   references {} via: {}".format(
                                other_obj, ", ".join(dependencies[obj][other_obj])
                            )
                        )
                raise BulkDataException("Cannot complete mapping")

            for obj in objs_without_deps:
                stack.append(obj)

                # Remove all dependencies on this object (they're satisfied)
                for other_obj in dependencies:
                    if obj in dependencies.get(other_obj):
                        del dependencies[other_obj][obj]

                # Remove this object from our remaining set.
                objs_remaining.remove(obj)

        return stack

    def _is_any_custom_api_name(self, api_name):
        """True if the entity name is custom (including any package)."""
        return api_name.endswith("__c")

    def _is_our_custom_api_name(self, api_name):
        """True if the entity name is custom and has our namespace prefix (if we have one)
        or if the entity does not have a namespace"""
        return self._is_any_custom_api_name(api_name) and (
            (
                self.options["namespace_prefix"]
                and api_name.startswith(self.options["namespace_prefix"])
            )
            or api_name.count("__") == 1
        )

    def _is_core_field(self, api_name):
        """True if this field is one that we should always include regardless
        of other settings or field configuration, such as Contact.FirstName.
        DB-level required fields don't need to be so handled."""

        return api_name in self.core_fields

    def _is_object_mappable(self, obj):
        """True if this object is one we can map, meaning it's an sObject and not
        some other kind of entity, it's not ignored, it's Bulk API compatible,
        and it's not in a hard-coded list of entities we can't currently handle."""

        return not any(
            [
                obj["name"] in self.options["ignore"],  # User-specified exclusions
                obj["name"].endswith(
                    "ChangeEvent"
                ),  # Change Data Capture entities (which get custom fields)
                obj["name"].endswith("__mdt"),  # Custom Metadata Types (MDAPI only)
                obj["name"].endswith("__e"),  # Platform Events
                obj["customSetting"],  # Not Bulk API compatible
                obj["name"]  # Objects we can't or shouldn't load/save
                in [
                    "User",
                    "Group",
                    "LookedUpFromActivity",
                    "OpenActivity",
                    "Task",
                    "Event",
                    "ActivityHistory",
                ],
            ]
        )

    def _is_field_mappable(self, obj, field):
        """True if this field is one we can map, meaning it's not ignored,
        it's createable by the Bulk API, it's not a deprecated field,
        and it's not a type of reference we can't handle without special
        configuration (self-lookup or reference to objects not included
        in this operation)."""
        return not any(
            [
                "{}.{}".format(obj, field["name"])  # User-ignored list
                in self.options["ignore"],
                "(Deprecated)" in field["label"],  # Deprecated managed fields
                field["type"] == "base64",  # No Bulk API support for base64 blob fields
                not field["createable"],  # Non-writeable fields
                field["type"] == "reference"  # Self-lookups
                and field["referenceTo"] == [obj],
                field["type"] == "reference"  # Outside lookups
                and not self._are_lookup_targets_in_operation(field),
            ]
        )

    def _is_required_field(self, field):
        """True if the field is either database-level required or a master-detail
        relationship field."""
        return (field["createable"] and not field["nillable"]) or (
            field["type"] == "reference" and field["relationshipOrder"] == 1
        )

    def _has_our_custom_fields(self, obj):
        """True if the object is owned by us or contains any field owned by us."""
        return any(
            [self._is_our_custom_api_name(field["name"]) for field in obj["fields"]]
        )

    def _are_lookup_targets_in_operation(self, field):
        """True if this lookup field aims at objects we are already including (all targets
        must match, although we don't provide actual support for polymorphism)."""
        return all([f in self.mapping_objects for f in field["referenceTo"]])

    def _is_lookup_to_included_object(self, field):
        """True if this field is a lookup and also references only objects we are
        already including."""
        return field["type"] == "reference" and self._are_lookup_targets_in_operation(
            field
        )


# For backwards-compatibility
QueryData = ExtractData


@contextmanager
def _download_file(uri, bulk_api):
    """Download the bulk API result file for a single batch"""
    resp = requests.get(uri, headers=bulk_api.headers(), stream=True)
    with tempfile.TemporaryFile("w+b") as f:
        for chunk in resp.iter_content(chunk_size=None):
            f.write(chunk)
        f.seek(0)
        yield f


def process_incoming_rows(f, record_type=None):
    if record_type and not isinstance(record_type, bytes):
        record_type = record_type.encode("utf-8")
    for line in f:
        if record_type:
            yield line.rstrip() + b"," + record_type + b"\n"
        else:
            yield line


def get_lookup_key_field(lookup, sf_field):
    return lookup.get("key_field", convert_to_snake_case(sf_field))
