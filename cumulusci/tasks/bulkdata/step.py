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

import lxml.etree as ET
import requests

from cumulusci.core.exceptions import BulkDataException
from cumulusci.core.utils import process_bool_arg


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


class UserDmlOperation(BaseDmlOperation):
    """
    "DmlOperation" to support User Lookups.

    - Users are not inserted by LoadData.
    - Instead, we need to query for Users to map the local and Salesforce IDs to populate downstream lookups.
    - A User is matched""
    """

    def __init__(self, *, sobject, operation, api_options, context, fields, task):
        super().__init__(
            sobject=sobject,
            operation=operation,
            api_options=api_options,
            context=context,
            fields=fields,
        )
        self.task = task

    def start(self):
        debug("UserDmlOperation.start", logger=self.task.logger.debug)
        self.records_processed = 0
        self.records = []
        self.sf_records = []
        self.sf_ids_by_value_by_field = {field: {} for field in self.fields}
        self.sf_records_by_id = {}

    def end(self):
        debug("UserDmlOperation.end", logger=self.task.logger.debug)
        record_failure_count = 0
        self.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS,
            [],
            self.records_processed,
            record_failure_count,
        )

    def load_records(self, records):
        all_records = list(records)
        self.records.extend(all_records)

        # Collect SF Ids by value
        fields = set()
        fields.add("Id")
        fields.update(self.fields)

        query = f"SELECT {','.join(fields)} FROM User"

        debug(query, logger=self.task.logger.warn)

        for record in self.task.sf.query(query)["records"]:
            self.sf_records.append(record)

            sf_id = record["Id"]

            self.sf_records_by_id[sf_id] = record

            for field in self.fields:
                value = record[field]

                sf_ids_by_value = self.sf_ids_by_value_by_field[field]
                sf_ids = sf_ids_by_value.get(value)
                if not sf_ids:
                    sf_ids = set()
                sf_ids.add(sf_id)
                sf_ids_by_value[value] = sf_ids
            self.records_processed += 1

        debug(
            {
                "fields": self.fields,
                "records": self.records,
                "sf_records": self.sf_records,
                "records_processed": self.records_processed,
                "sf_ids_by_value_by_field": self.sf_ids_by_value_by_field,
            },
            title="UserDmlOperation.load_records",
            logger=self.task.logger.debug,
        )

    def get_results(self):
        """Return a generator of DataOperationResult objects."""
        default_user_id = self.task.org_config.user_id

        results = []
        for record in self.records:
            all_sf_ids = []

            for index, field in enumerate(self.fields):
                value = record[index]
                sf_ids_by_value = self.sf_ids_by_value_by_field[field]
                if value in sf_ids_by_value:
                    all_sf_ids.append(sf_ids_by_value[value])
                else:
                    all_sf_ids.append(set())

            sf_ids = set.intersection(*all_sf_ids)

            if not sf_ids:
                sf_ids.add(default_user_id)
            success = len(sf_ids) == 1
            error = (
                None
                if success
                else f"More than one User record found with the same field values: {', '.join(self.fields)}"
            )
            sf_id = next(iter(sf_ids))

            results.append(DataOperationResult(sf_id, success, error))

        debug(
            {
                "default_user_id": default_user_id,
                "fields": self.fields,
                "records": self.records,
                "sf_records": self.sf_records,
                "sf_ids_by_value_by_field": self.sf_ids_by_value_by_field,
                "results": results,
            },
            title="UserDmlOperation.get_results",
            logger=self.task.logger.warn,
        )

        for result in results:
            yield result
