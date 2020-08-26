from abc import ABCMeta, abstractmethod
from collections import namedtuple
from contextlib import contextmanager
import csv
from enum import Enum
import io
import os
import pathlib
import tempfile
import time
import copy

import lxml.etree as ET
import requests

from cumulusci.core.exceptions import BulkDataException
from cumulusci.core.utils import process_bool_arg


# TODO: remove temporary debugging or find a place for code
def debug(value, title=None, indent=0, tab="  ", show_list_index=True, logger=None):
    indentation = tab * (indent)
    prefix = "" if title is None else str(title) + " : "
    if isinstance(value, dict):
        logger(indentation + prefix + "{")
        for key, dict_value in value.items():
            debug(
                dict_value,
                title=key,
                indent=(indent + 1),
                tab=tab,
                show_list_index=show_list_index,
                logger=logger,
            )
        logger(indentation + "}" + ("," if indent else ""))
    elif isinstance(value, list):
        logger(indentation + prefix + "[")
        for index, list_item in enumerate(value):
            title = index if show_list_index else None
            debug(
                list_item,
                title=title,
                indent=(indent + 1),
                tab=tab,
                show_list_index=show_list_index,
                logger=logger,
            )
        logger(indentation + "]" + ("," if indent else ""))
    elif isinstance(value, set):
        logger(indentation + prefix + "set(")
        for index, list_item in enumerate(value):
            debug(
                list_item,
                title=index,
                indent=(indent + 1),
                tab=tab,
                show_list_index=show_list_index,
                logger=logger,
            )
        logger(indentation + ")" + ("," if indent else ""))
    else:
        logger(indentation + prefix + str(value) + ("," if indent else ""))


class DataOperationType(Enum):
    """Enum defining the API data operation requested."""

    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    HARD_DELETE = "hardDelete"
    QUERY = "query"


class DataApi(Enum):
    """Enum defining requested Salesforce data API for an operation."""

    BULK = "bulk"
    REST = "rest"


class DataOperationStatus(Enum):
    """Enum defining outcome values for a data operation."""

    SUCCESS = "Success"
    ROW_FAILURE = "Row failure"
    JOB_FAILURE = "Job failure"
    IN_PROGRESS = "In progress"
    ABORTED = "Aborted"


DataOperationResult = namedtuple("Result", ["id", "success", "error"])
DataOperationJobResult = namedtuple(
    "DataOperationJobResult",
    ["status", "job_errors", "records_processed", "total_row_errors"],
)


@contextmanager
def download_file(uri, bulk_api):
    """Download the Bulk API result file for a single batch,
    and remove it when the context manager exits."""
    try:
        (handle, path) = tempfile.mkstemp(text=False)
        resp = requests.get(uri, headers=bulk_api.headers(), stream=True)
        resp.raise_for_status()
        f = os.fdopen(handle, "wb")
        for chunk in resp.iter_content(chunk_size=None):
            f.write(chunk)

        f.close()
        with open(path, "r", newline="", encoding="utf-8") as f:
            yield f
    finally:
        pathlib.Path(path).unlink()


class BulkJobMixin:
    """Provides mixin utilities for classes that manage Bulk API jobs."""

    def _job_state_from_batches(self, job_id):
        """Query for batches under job_id and return overall status
        inferred from batch-level status values."""
        uri = f"{self.bulk.endpoint}/job/{job_id}/batch"
        response = requests.get(uri, headers=self.bulk.headers())
        response.raise_for_status()
        return self._parse_job_state(response.content)

    def _parse_job_state(self, xml):
        """Parse the Bulk API return value and generate a summary status record for the job."""
        tree = ET.fromstring(xml)
        statuses = [el.text for el in tree.iterfind(".//{%s}state" % self.bulk.jobNS)]
        state_messages = [
            el.text for el in tree.iterfind(".//{%s}stateMessage" % self.bulk.jobNS)
        ]

        failures = tree.find(".//{%s}numberRecordsFailed" % self.bulk.jobNS)
        record_failure_count = int(failures.text) if failures is not None else 0
        processed = tree.find(".//{%s}numberRecordsProcessed" % self.bulk.jobNS)
        records_processed = int(processed.text) if processed is not None else 0

        # FIXME: "Not Processed" to be expected for original batch with PK Chunking Query
        # PK Chunking is not currently supported.
        if "Not Processed" in statuses:
            return DataOperationJobResult(
                DataOperationStatus.ABORTED, [], records_processed, record_failure_count
            )
        elif "InProgress" in statuses or "Queued" in statuses:
            return DataOperationJobResult(
                DataOperationStatus.IN_PROGRESS,
                [],
                records_processed,
                record_failure_count,
            )
        elif "Failed" in statuses:
            return DataOperationJobResult(
                DataOperationStatus.JOB_FAILURE,
                state_messages,
                records_processed,
                record_failure_count,
            )

        if record_failure_count:
            return DataOperationJobResult(
                DataOperationStatus.ROW_FAILURE,
                [],
                records_processed,
                record_failure_count,
            )

        return DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], records_processed, record_failure_count
        )

    def _wait_for_job(self, job_id):
        """Wait for the given job to enter a completed state (success or failure)."""
        while True:
            job_status = self.bulk.job_status(job_id)
            self.logger.info(
                f"Waiting for job {job_id} ({job_status['numberBatchesCompleted']}/{job_status['numberBatchesTotal']} batches complete)"
            )
            result = self._job_state_from_batches(job_id)
            if result.status is not DataOperationStatus.IN_PROGRESS:
                break

            time.sleep(10)
        self.logger.info(f"Job {job_id} finished with result: {result.status.value}")
        if result.status is DataOperationStatus.JOB_FAILURE:
            for state_message in result.job_errors:
                self.logger.error(f"Batch failure message: {state_message}")

        return result


class BaseDataOperation(metaclass=ABCMeta):
    """Abstract base class for all data operations (queries and DML)."""

    def __init__(self, *, sobject, operation, api_options, context):
        self.sobject = sobject
        self.operation = operation
        self.api_options = api_options
        self.context = context
        self.bulk = context.bulk
        self.sf = context.sf
        self.logger = context.logger
        self.job_result = None


class BaseQueryOperation(BaseDataOperation, metaclass=ABCMeta):
    """Abstract base class for query operations in all APIs."""

    def __init__(self, *, sobject, api_options, context, query):
        super().__init__(
            sobject=sobject,
            operation=DataOperationType.QUERY,
            api_options=api_options,
            context=context,
        )
        self.soql = query

    def __enter__(self):
        self.query()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    @abstractmethod
    def query(self):
        """Execute requested query and block until results are available."""
        pass

    @abstractmethod
    def get_results(self):
        """Return a generator of rows from the query."""
        pass


class BulkApiQueryOperation(BaseQueryOperation, BulkJobMixin):
    """Operation class for Bulk API query jobs."""

    def query(self):
        self.job_id = self.bulk.create_query_job(self.sobject, contentType="CSV")
        self.logger.info(f"Created Bulk API query job {self.job_id}")
        self.batch_id = self.bulk.query(self.job_id, self.soql)

        self.job_result = self._wait_for_job(self.job_id)
        self.bulk.close_job(self.job_id)

    def get_results(self):
        # FIXME: For PK Chunking, need to get new batch Ids
        # and retrieve their results. Original batch will not be processed.

        result_ids = self.bulk.get_query_batch_result_ids(
            self.batch_id, job_id=self.job_id
        )
        for result_id in result_ids:
            uri = f"{self.bulk.endpoint}/job/{self.job_id}/batch/{self.batch_id}/result/{result_id}"

            with download_file(uri, self.bulk) as f:
                reader = csv.reader(f)
                self.headers = next(reader)
                if "Records not found for this query" in self.headers:
                    return

                yield from reader


class BaseDmlOperation(BaseDataOperation, metaclass=ABCMeta):
    """Abstract base class for DML operations in all APIs."""

    def __init__(self, *, sobject, operation, api_options, context, fields):
        super().__init__(
            sobject=sobject,
            operation=operation,
            api_options=api_options,
            context=context,
        )
        self.fields = fields

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end()

    @abstractmethod
    def start(self):
        """Perform any required setup, such as job initialization, for the operation."""
        pass

    @abstractmethod
    def load_records(self, records):
        """Perform the requested DML operation on the supplied row iterator."""
        pass

    @abstractmethod
    def end(self):
        """Perform any required teardown for the operation before results are returned."""
        pass

    @abstractmethod
    def get_results(self):
        """Return a generator of DataOperationResult objects."""
        pass


class BulkApiDmlOperation(BaseDmlOperation, BulkJobMixin):
    """Operation class for all DML operations run using the Bulk API."""

    def __init__(self, *, sobject, operation, api_options, context, fields):
        super().__init__(
            sobject=sobject,
            operation=operation,
            api_options=api_options,
            context=context,
            fields=fields,
        )
        self.csv_buff = io.StringIO(newline="")
        self.csv_writer = csv.writer(self.csv_buff)

    def start(self):
        self.job_id = self.bulk.create_job(
            self.sobject,
            self.operation.value,
            contentType="CSV",
            concurrency=self.api_options.get("bulk_mode", "Parallel"),
        )

    def end(self):
        self.bulk.close_job(self.job_id)
        self.job_result = self._wait_for_job(self.job_id)

    def load_records(self, records):
        self.batch_ids = []

        for count, csv_batch in enumerate(self._batch(records)):
            self.context.logger.info(f"Uploading batch {count + 1}")
            self.batch_ids.append(self.bulk.post_batch(self.job_id, iter(csv_batch)))

    def _batch(self, records, n=10000, char_limit=10_000_000):
        """Given an iterator of records, yields batches of
        records serialized in .csv format.

        Batches adhere to the following, in order of presedence:
        (1) They do not exceed the given character limit
        (2) They do not contain more than n records per batch
        """
        serialized_csv_fields = self._serialize_csv_record(self.fields)
        len_csv_fields = len(serialized_csv_fields)

        # append fields to first row
        batch = [serialized_csv_fields]
        current_chars = len_csv_fields
        for record in records:
            serialized_record = self._serialize_csv_record(record)
            # Does the next record put us over the character limit?
            if len(serialized_record) + current_chars > char_limit:
                yield batch
                batch = [serialized_csv_fields]
                current_chars = len_csv_fields

            batch.append(serialized_record)
            current_chars += len(serialized_record)

            # yield batch if we're at desired size
            # -1 due to first row being field names
            if len(batch) - 1 == n:
                yield batch
                batch = [serialized_csv_fields]
                current_chars = len_csv_fields

        # give back anything leftover
        if len(batch) > 1:
            yield batch

    def _serialize_csv_record(self, record):
        """Given a list of strings (record) return
        the corresponding record serialized in .csv format"""
        self.csv_writer.writerow(record)
        serialized = self.csv_buff.getvalue().encode("utf-8")
        # flush buffer
        self.csv_buff.truncate(0)
        self.csv_buff.seek(0)

        return serialized

    def get_results(self):
        for batch_id in self.batch_ids:
            try:
                results_url = (
                    f"{self.bulk.endpoint}/job/{self.job_id}/batch/{batch_id}/result"
                )
                # Download entire result file to a temporary file first
                # to avoid the server dropping connections
                with download_file(results_url, self.bulk) as f:
                    self.logger.info(f"Downloaded results for batch {batch_id}")

                    reader = csv.reader(f)
                    next(reader)  # skip header

                    for row in reader:
                        success = process_bool_arg(row[1])
                        yield DataOperationResult(
                            row[0] if success else None,
                            success,
                            row[3] if not success else None,
                        )
            except Exception as e:
                raise BulkDataException(
                    f"Failed to download results for batch {batch_id} ({str(e)})"
                )


class ReadOnlyDmlOperation(BaseDmlOperation):
    """
    TODO
    """

    def __init__(
        self, *, sobject, operation, api_options, context, fields, task, optional_fields
    ):
        super().__init__(
            sobject=sobject,
            operation=operation,
            api_options=api_options,
            context=context,
            fields=fields,
        )
        self.task = task
        self.optional_fields = set()
        if optional_fields:
            self.optional_fields.update(optional_fields)
        # Only keep optional_fields that are in fields
        self.optional_fields.intersection_update(self.fields)

    def start(self):
        # TODO: remove debugging
        debug("ReadOnlyDmlOperation.start", logger=self.task.logger.debug)
        self.db_records = []

    def end(self):
        self.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS,
            [],
            len(self.db_records),  # records_processed
            0,  # record_failure_count
        )
        # TODO: remove debugging
        debug(
            self.job_result,
            title="ReadOnlyDmlOperation.end",
            logger=self.task.logger.debug,
        )

    def load_records(self, db_records):
        """
        Our goal is to match sf_record to db_records.

        - We do this by returning a list of DataOperationResult in the exact same indexical order
        as the db_records given to use.
        - DataOperationResult has no information about the db_record and only has information about the sf_id.
        - LoadData creates a collection of tuples (db_id, sf_id) to insert into the mapping's ID table by enumerating db_records and the return value of get_results index-wise.

        So the point of load_records is only to collect the db_records given in the exact order retrieved.
        load_records may be called several times given only a batch of db_records.
        """
        self.db_records.extend(list(db_records))

    def get_results(self):
        """
        NOTE: Return a generator of DataOperationResult objects.

        We need to match a sf_record for each db_record.  We say a sf_record "matches" a db_record if:

        - We find only one sf_record that has the same field values as the db_record
        - We loop through field values until we find only one sf_record that matches db_record's field value
        - If no sf_records match a db_record field value, we ignore that field.   e.g. User.Username is different for each default scratch org user.
        - When creating a mapping for a Read-Only SObject, try to only include enough field values to uniquly identify records.
            - For most SObjects, there is a unique field, e.g. DeveloperName.
            - This gets more complicated for User.

        IDEA
        ----

        1. Query all records for this object.   TODO: Query records in a safe way for largish data volumes.
            - Collect the sf_ids by field and field values
        2. Match db_records to sf_records by loop through db_records and trying to find only one sf_record that matches db_record's field value.
            - optional_fields can be ignored from matching if no sf_records match db_record's field value.
            - If no sf_record matches all of db_record's field value (except for optional_fields), map a NULL sf_id to the db_record.
            - Give an error in DataOperationResult if more than sf_record matches db_record field values.

        """
        # Query all records for this object.
        # TODO: do a better job to handle large data volumes.
        fields = set()
        fields.add("Id")
        fields.update(self.fields)

        query = f"SELECT {','.join(fields)} FROM {self.sobject}"

        debug(query, logger=self.task.logger.warn)

        sf_ids_by_value_by_field = {field: {} for field in self.fields}
        for sf_record in self.task.sf.query_all_iter(query):
            sf_id = sf_record["Id"]

            # For each field, collect which sf_records have each field value.
            for field in self.fields:
                value = sf_record[field]

                sf_ids_by_value = sf_ids_by_value_by_field[field]

                sf_ids = sf_ids_by_value.get(value)
                if not sf_ids:
                    sf_ids = set()

                sf_ids.add(sf_id)
                sf_ids_by_value[value] = sf_ids

        # TODO: remove debugging
        debug(
            {
                "fields": self.fields,
                "db_records": self.db_records,
                "sf_ids_by_value_by_field": sf_ids_by_value_by_field,
            },
            title="ReadOnlyDmlOperation.load_records",
            logger=self.task.logger.debug,
        )

        # Match db_records to sf_records
        for db_record in self.db_records:
            sf_ids_with_all_field_values = None

            # TODO: remove debugging
            _sf_ids_by_field_debug = {}

            for index, field in enumerate(self.fields):
                value = db_record[index]
                sf_ids_with_value = sf_ids_by_value_by_field[field].get(value, set())

                _sf_ids_by_field_debug[field] = sf_ids_with_value

                # Do not require finding a field value match for optional_fields
                if not sf_ids_with_value and field in self.optional_fields:
                    continue

                if sf_ids_with_all_field_values is None:
                    sf_ids_with_all_field_values = copy.deepcopy(sf_ids_with_value)
                else:
                    # Intersect existing intersection
                    sf_ids_with_all_field_values.intersection_update(sf_ids_with_value)

                # Stop if we only have 0 or 1 sf_id matching all tested field values.
                if len(sf_ids_with_all_field_values) < 2:
                    break

            sf_id = (
                next(iter(sf_ids_with_all_field_values))
                if len(sf_ids_with_all_field_values) == 1
                else None
            )
            success = (
                len(sf_ids_with_all_field_values) < 2
            )  # TODO: maybe have a kwarg specify if task should allow records not to be found
            error = (
                None
                if len(sf_ids_with_all_field_values) < 2
                else f"More than one {self.sobject} record found with the same field values for {', '.join(self.fields)} (except for {', '.join(self.optional_fields)}): {', '.join(sf_ids_with_all_field_values)}"
            )

            # TODO: remove debugging
            debug(
                {
                    "db_record": db_record,
                    "_sf_ids_by_field_debug": _sf_ids_by_field_debug,
                    "sf_ids_with_all_field_values": sf_ids_with_all_field_values,
                    "sf_id": sf_id,
                    "success": success,
                    "error": error,
                },
                title="get_results result",
                logger=self.task.logger.warn,
            )

            yield DataOperationResult(sf_id, success, error)
