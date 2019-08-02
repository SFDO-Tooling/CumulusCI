import datetime
import requests
import tempfile
import time
import unicodecsv
import xml.etree.ElementTree as ET

from contextlib import contextmanager
from sqlalchemy import types
from sqlalchemy import event
from sqlalchemy import Table

from cumulusci.utils import convert_to_snake_case


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
