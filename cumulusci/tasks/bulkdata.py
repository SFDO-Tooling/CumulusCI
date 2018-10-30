from future import standard_library

standard_library.install_aliases()
from builtins import zip
from contextlib import contextmanager
import csv
import datetime
import io
import itertools
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
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy import text
from sqlalchemy import types
from sqlalchemy import event
import requests
import unicodecsv

from cumulusci.core.utils import process_bool_arg, ordered_yaml_load
from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils import log_progress

# TODO: UserID Catcher
# TODO: Dater


# Create a custom sqlalchemy field type for sqlite datetime fields which are stored as integer of epoch time
class EpochType(types.TypeDecorator):
    impl = types.Integer

    epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)

    def process_bind_param(self, value, dialect):
        return int((value - self.epoch).total_seconds()) * 1000

    def process_result_value(self, value, dialect):
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
        completed = 0
        pending = 0
        failed = 0
        for el in tree.iterfind(".//{%s}state" % self.bulk.jobNS):
            state = el.text
            if state == "Not Processed":
                return "Aborted"
            elif state == "Failed":
                failed += 1
            elif state == "Completed":
                completed += 1
            else:  # Queued, InProgress
                pending += 1
        if pending:
            return "InProgress"
        elif failed:
            return "Failed"
        else:
            return "Completed"

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
            result = self._job_state_from_batches(job_id)
            if result != "InProgress":
                break
            time.sleep(10)
        self.logger.info("Job {} finished with result: {}".format(job_id, result))
        return result

    def _sql_bulk_insert_from_csv(self, conn, table, columns, data_file):
        if conn.dialect.name == "psycopg2":
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
        if not isinstance(self.options["objects"], list):
            self.options["objects"] = [
                obj.strip() for obj in self.options["objects"].split(",")
            ]

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
    }

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
                break

    def _load_mapping(self, mapping):
        """Load data for a single step."""
        job_id, local_ids_for_batch = self._create_job(mapping)
        result = self._wait_for_job(job_id)
        # We store inserted ids even if some batches failed
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
        fields = mapping["fields"].copy()
        del fields["Id"]
        id_column = model.__table__.primary_key.columns.keys()[0]
        columns = [getattr(model, id_column)]

        for f in fields.values():
            columns.append(model.__table__.columns[f])
        lookups = mapping.get("lookups", {}).copy().values()
        for lookup in lookups:
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
        for lookup in lookups:
            # Outer join with lookup ids table:
            # returns main obj even if lookup is null
            value_column = getattr(model, lookup["key_field"])
            query = query.outerjoin(
                lookup["aliased_table"],
                lookup["aliased_table"].columns.id == value_column,
            )
            # Order by foreign key to minimize lock contention
            # by trying to keep lookup targets in the same batch
            lookup_column = getattr(model, lookup["key_field"])
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
            except Exception:  # pragma: nocover
                # If we can't download one result file,
                # don't let that stop us from downloading the others
                self.logger.error(
                    "Could not download batch results: {}".format(batch_id)
                )
                continue
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
                    self.logger.warning("      Error on row {}: {}".format(i, row[3]))
                i += 1

        # Bulk insert rows into id table
        columns = ("id", "sf_id")
        data_file = IteratorBytesIO(produce_csv())
        self._sql_bulk_insert_from_csv(conn, id_table_name, columns, data_file)

    def _init_db(self):
        # initialize the DB engine
        self.engine = create_engine(self.options["database_url"])

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

        # initialize the DB session
        self.session = Session(self.engine)

    def _init_mapping(self):
        with open(self.options["mapping"], "r") as f:
            self.mapping = ordered_yaml_load(f)


class QueryData(BulkJobTaskMixin, BaseSalesforceApiTask):
    task_options = {
        "database_url": {
            "description": "A DATABASE_URL where the query output should be written",
            "required": True,
        },
        "mapping": {
            "description": "The path to a yaml file containing mappings of the database fields to Salesforce object fields",
            "required": True,
        },
    }

    def _run_task(self):
        self._init_mapping()
        self._init_db()

        for mapping in self.mappings.values():
            soql = self._soql_for_mapping(mapping)
            self._run_query(soql, mapping)

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
        fields = [field["sf"] for field in self._fields_for_mapping(mapping)]
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
        for sf in sf_header:
            if sf == "Records not found for this query":
                return
            if sf:
                column = mapping["fields"].get(sf)
                if not column:
                    column = mapping.get("lookups", {}).get(sf, {}).get("key_field")
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
        self._sql_bulk_insert_from_csv(conn, mapping["table"], columns, data_file)
        self.session.commit()

    def _create_tables(self):
        for mapping in self.mappings.values():
            self._create_table(mapping)
        self.metadata.create_all()

    def _create_table(self, mapping):
        model_name = "{}Model".format(mapping["table"])
        mapper_kwargs = {}
        table_kwargs = {}
        if mapping["table"] in self.models:
            raise BulkDataException("Table already exists: {}".format(mapping["table"]))
        self.models[mapping["table"]] = type(model_name, (object,), {})

        id_column = mapping["fields"].get("Id") or "id"
        fields = []
        fields.append(Column(id_column, Unicode(255), primary_key=True))
        for field in self._fields_for_mapping(mapping):
            if field["sf"] == "Id":
                continue
            fields.append(Column(field["db"], Unicode(255)))
        if "record_type" in mapping:
            fields.append(Column("record_type", Unicode(255)))
        t = Table(mapping["table"], self.metadata, *fields, **table_kwargs)

        mapper(self.models[mapping["table"]], t, **mapper_kwargs)

    def _fields_for_mapping(self, mapping):
        fields = []
        for sf_field, db_field in mapping.get("fields", {}).items():
            fields.append({"sf": sf_field, "db": db_field})
        for sf_field, lookup in mapping.get("lookups", {}).items():
            fields.append({"sf": sf_field, "db": lookup["key_field"]})
        return fields


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
            yield line + b"," + record_type + b"\n"
        else:
            yield line
