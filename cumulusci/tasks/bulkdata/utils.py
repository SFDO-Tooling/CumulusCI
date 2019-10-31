import datetime
import io
import requests
import tempfile
import time
import unicodecsv
import xml.etree.ElementTree as ET
from contextlib import contextmanager

from sqlalchemy import types
from sqlalchemy import event
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy.orm import mapper

from cumulusci.utils import convert_to_snake_case
from cumulusci.core.exceptions import BulkDataException


@contextmanager
def download_file(uri, bulk_api):
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
        uri = f"{self.bulk.endpoint}/job/{job_id}/batch"
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
                f"    Waiting for job {job_id} ({job_status['numberBatchesCompleted']}/{job_status['numberBatchesTotal']})"
            )
            result, messages = self._job_state_from_batches(job_id)
            if result != "InProgress":
                break
            time.sleep(10)
        self.logger.info(f"Job {job_id} finished with result: {result}")
        if result == "Failed":
            for state_message in messages:
                self.logger.error(f"Batch failure message: {state_message}")

        return result

    def _sql_bulk_insert_from_csv(self, conn, table, columns, data_file):
        if conn.dialect.name in ("postgresql", "psycopg2"):
            # psycopg2 (the postgres driver) supports COPY FROM
            # to efficiently bulk insert rows in CSV format
            with conn.connection.cursor() as cursor:
                cursor.copy_expert(
                    f"COPY {table} ({','.join(columns)}) FROM STDIN WITH (FORMAT CSV)",
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

    def _create_record_type_table(self, table_name):
        rt_map_model_name = f"{table_name}Model"
        self.models[table_name] = type(rt_map_model_name, (object,), {})
        rt_map_fields = [
            Column("record_type_id", Unicode(18), primary_key=True),
            Column("developer_name", Unicode(255)),
        ]
        rt_map_table = Table(table_name, self.metadata, *rt_map_fields)
        mapper(self.models[table_name], rt_map_table)

    def _extract_record_types(self, sobject, table, conn):
        self.logger.info(f"Extracting Record Types for {sobject}")
        query = (
            f"SELECT Id, DeveloperName FROM RecordType WHERE SObjectType='{sobject}'"
        )
        data_file = io.BytesIO()
        writer = unicodecsv.writer(data_file)
        for rt in self.sf.query(query)["records"]:
            writer.writerow([rt["Id"], rt["DeveloperName"]])
        data_file.seek(0)

        self._sql_bulk_insert_from_csv(
            conn, table, ["record_type_id", "developer_name"], data_file
        )


def _handle_primary_key(mapping, fields):
    # Provide support for legacy mappings which used the OID as the pk but
    # default to using an autoincrementing int pk and a separate sf_id column
    mapping["oid_as_pk"] = bool(mapping.get("fields", {}).get("Id"))
    if mapping["oid_as_pk"]:
        id_column = mapping["fields"]["Id"]
        fields.append(Column(id_column, Unicode(255), primary_key=True))
    else:
        fields.append(Column("id", Integer(), primary_key=True, autoincrement=True))


def create_table(mapping, metadata):
    """Given a mapping data structure (from mapping.yml) and SQLAlchemy
       metadata, create a table matching the mapping.

       Mapping should be a dict-like with keys "fields", "table" and
       optionally "oid_as_pk" and "record_type" """

    fields = []
    _handle_primary_key(mapping, fields)

    # make a field list to create
    for field in fields_for_mapping(mapping):
        if mapping["oid_as_pk"] and field["sf"] == "Id":
            continue
        fields.append(Column(field["db"], Unicode(255)))

    if "record_type" in mapping:
        fields.append(Column("record_type", Unicode(255)))
    t = Table(mapping["table"], metadata, *fields)
    if t.exists():
        raise BulkDataException(f"Table already exists: {mapping['table']}")
    return t


def fields_for_mapping(mapping):
    """Summarize the list of fields in a table mapping"""
    fields = []
    for sf_field, db_field in mapping.get("fields", {}).items():
        fields.append({"sf": sf_field, "db": db_field})
    for sf_field, lookup in mapping.get("lookups", {}).items():
        fields.append({"sf": sf_field, "db": get_lookup_key_field(lookup, sf_field)})
    return fields


def generate_batches(num_records, batch_size):
    """Generate batch size list for splitting a number of tasks into batch jobs.

    Given a number of records to split up, and a batch size, generate a
    stream of batchsize, index pairs"""
    num_batches = (num_records // batch_size) + 1
    for i in range(0, num_batches):
        if i == num_batches - 1:  # last batch
            batch_size = num_records - (batch_size * i)  # leftovers
        if batch_size > 0:
            yield batch_size, i
