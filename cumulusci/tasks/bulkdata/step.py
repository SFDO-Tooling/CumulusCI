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
from cumulusci.tasks.bulkdata.utils import batch_iterator


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

    SUCCESS = "Succeeded"
    FAILURE = "Failed"


DataOperationResult = namedtuple("Result", ["id", "success", "error"])


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
        with open(path, "r") as f:
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
        """Parse the Bulk API return value and generate a summary status value for the job."""
        tree = ET.fromstring(xml)
        statuses = [el.text for el in tree.iterfind(".//{%s}state" % self.bulk.jobNS)]
        state_messages = [
            el.text for el in tree.iterfind(".//{%s}stateMessage" % self.bulk.jobNS)
        ]

        # FIXME: "Not Processed" to be expected for original batch with PK Chunking Query
        # PK Chunking is not currently supported.
        if "Not Processed" in statuses:
            return "Aborted", None
        elif "InProgress" in statuses or "Queued" in statuses:
            return "InProgress", None
        elif "Failed" in statuses:
            return "Failed", state_messages

        failures = tree.find(".//{%s}numberRecordsFailed" % self.bulk.jobNS)
        if failures is not None:
            num_failures = int(failures.text)
            if num_failures:
                return "CompletedWithFailures", [f"Failures detected: {num_failures}"]

        return "Completed", None

    def _wait_for_job(self, job_id):
        """Wait for the given job to enter a completed state (success or failure)."""
        while True:
            job_status = self.bulk.job_status(job_id)
            self.logger.info(
                f"Waiting for job {job_id} ({job_status['numberBatchesCompleted']}/{job_status['numberBatchesTotal']})"
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


class BaseDataOperation(metaclass=ABCMeta):
    """Abstract base class for all data operations (queries and DML)."""

    def __init__(self, sobject, operation, api_options, context):
        self.sobject = sobject
        self.operation = operation
        self.api_options = api_options
        self.context = context
        self.bulk = context.bulk
        self.sf = context.sf
        self.logger = context.logger
        self.status = None


class BaseQueryOperation(BaseDataOperation, metaclass=ABCMeta):
    """Abstract base class for query operations in all APIs."""

    def __init__(self, sobject, api_options, context, query):
        super().__init__(sobject, DataOperationType.QUERY, api_options, context)
        self.soql = query

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
        self.batch_id = self.bulk.query(self.job_id, self.soql)

        result = self._wait_for_job(self.job_id)
        if result in ["Completed", "CompletedWithFailures"]:
            self.status = DataOperationStatus.SUCCESS
        else:
            self.status = DataOperationStatus.FAILURE

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

    def __init__(self, sobject, operation, api_options, context, fields):
        super().__init__(sobject, operation, api_options, context)
        self.fields = fields

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

    def start(self):
        self.job_id = self.bulk.create_job(
            self.sobject,
            self.operation.value,
            contentType="CSV",
            concurrency=self.api_options.get("bulk_mode", "Parallel"),
        )

    def end(self):
        self.bulk.close_job(self.job_id)
        result = self._wait_for_job(self.job_id)
        if result in ["Completed", "CompletedWithFailures"]:
            self.status = DataOperationStatus.SUCCESS
        else:
            self.status = DataOperationStatus.FAILURE

    def load_records(self, records):
        self.batch_ids = []

        for count, csv_batch in enumerate(self._batch(records)):
            self.context.logger.info(f"Uploading batch {count + 1}")
            self.batch_ids.append(self.bulk.post_batch(self.job_id, csv_batch))

    def _batch(self, records):
        """Return a generator of generators, where each child generator is batched."""
        for batch in batch_iterator(records, self.api_options.get("batch_size", 10000)):
            yield self._csv_generator(batch)

    def _csv_generator(self, records):
        """Return a generator of binary, CSV-format data for the given record iterator."""
        content = io.StringIO()
        writer = csv.writer(content)
        writer.writerow(self.fields)

        content.seek(0)
        yield content.read().encode("utf-8")
        for rec in records:
            content = io.StringIO()
            writer = csv.writer(content)
            writer.writerow(rec)
            content.seek(0)

            yield content.read().encode("utf-8")

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
