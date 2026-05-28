import csv
import io
import json
import os
import pathlib
import tempfile
import time
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from itertools import tee
from typing import Any, Dict, List, NamedTuple, Optional, Union
from urllib.parse import quote

import requests
import salesforce_bulk

from cumulusci.core.enums import StrEnum
from cumulusci.core.exceptions import BulkDataException
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.bulkdata.select_utils import (
    SelectOperationExecutor,
    SelectRecordRetrievalMode,
    SelectStrategy,
    split_and_filter_fields,
)
from cumulusci.tasks.bulkdata.utils import DataApi, iterate_in_chunks
from cumulusci.utils.classutils import namedtuple_as_simple_dict
from cumulusci.utils.xml import lxml_parse_string

DEFAULT_BULK_BATCH_SIZE = 10_000
DEFAULT_REST_BATCH_SIZE = 200
MAX_REST_BATCH_SIZE = 200
HIGH_PRIORITY_VALUE = 3
LOW_PRIORITY_VALUE = 0.5
csv.field_size_limit(2**27)  # 128 MB


class DataOperationType(StrEnum):
    """Enum defining the API data operation requested."""

    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    HARD_DELETE = "hardDelete"
    QUERY = "query"
    UPSERT = "upsert"
    ETL_UPSERT = "etl_upsert"
    SMART_UPSERT = "smart_upsert"  # currently undocumented
    SELECT = "select"


class DataOperationStatus(StrEnum):
    """Enum defining outcome values for a data operation."""

    SUCCESS = "Success"
    ROW_FAILURE = "Row failure"
    JOB_FAILURE = "Job failure"
    IN_PROGRESS = "In progress"
    ABORTED = "Aborted"


class DataOperationResult(NamedTuple):
    id: str
    success: bool
    error: str
    created: Optional[bool] = None


class DataOperationJobResult(NamedTuple):
    status: DataOperationStatus
    job_errors: List[str]
    records_processed: int
    total_row_errors: int = 0

    def simplify(self):
        return namedtuple_as_simple_dict(self)


@contextmanager
def download_file(uri, bulk_api, *, chunk_size=8192):
    """Download the Bulk API result file for a single batch,
    and remove it when the context manager exits."""
    try:
        (handle, path) = tempfile.mkstemp(text=False)
        resp = requests.get(uri, headers=bulk_api.headers(), stream=True)
        resp.raise_for_status()
        f = os.fdopen(handle, "wb")
        for chunk in resp.iter_content(chunk_size=chunk_size):  # VCR needs a chunk_size
            # specific chunk_size seems to make no measurable perf difference
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

    def _parse_job_state(self, xml: str):
        """Parse the Bulk API return value and generate a summary status record for the job."""
        tree = lxml_parse_string(xml)
        statuses = [el.text for el in tree.iterfind(".//{%s}state" % self.bulk.jobNS)]
        state_messages = [
            el.text for el in tree.iterfind(".//{%s}stateMessage" % self.bulk.jobNS)
        ]

        # Get how many total records failed across all the batches.
        failures = tree.findall(".//{%s}numberRecordsFailed" % self.bulk.jobNS)
        record_failure_count = sum([int(failure.text) for failure in (failures or [])])

        # Get how many total records processed across all the batches.
        processed = tree.findall(".//{%s}numberRecordsProcessed" % self.bulk.jobNS)
        records_processed_count = sum(
            [int(processed.text) for processed in (processed or [])]
        )
        # FIXME: "Not Processed" to be expected for original batch with PK Chunking Query
        # PK Chunking is not currently supported.
        if "Not Processed" in statuses:
            return DataOperationJobResult(
                DataOperationStatus.ABORTED,
                [],
                records_processed_count,
                record_failure_count,
            )
        elif "InProgress" in statuses or "Queued" in statuses:
            return DataOperationJobResult(
                DataOperationStatus.IN_PROGRESS,
                [],
                records_processed_count,
                record_failure_count,
            )
        elif "Failed" in statuses:
            return DataOperationJobResult(
                DataOperationStatus.JOB_FAILURE,
                state_messages,
                records_processed_count,
                record_failure_count,
            )

        # All the records submitted in this job failed.
        if record_failure_count:
            return DataOperationJobResult(
                DataOperationStatus.ROW_FAILURE,
                [],
                records_processed_count,
                record_failure_count,
            )

        return DataOperationJobResult(
            DataOperationStatus.SUCCESS,
            [],
            records_processed_count,
            record_failure_count,
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
        plural_errors = "Errors" if result.total_row_errors != 1 else "Error"
        errors = (
            f": {result.total_row_errors} {plural_errors}"
            if result.total_row_errors
            else ""
        )
        self.logger.info(
            f"Job {job_id} finished with result: {result.status.value}{errors}"
        )
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


class RestApiQueryOperation(BaseQueryOperation):
    """Operation class for REST API query jobs."""

    def __init__(self, *, sobject, fields, api_options, context, query):
        super().__init__(
            sobject=sobject, api_options=api_options, context=context, query=query
        )
        self.fields = fields

    def query(self):
        self.response = self.sf.query(self.soql)
        self.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], self.response["totalSize"], 0
        )

    def get_results(self):
        def convert(rec):
            return [str(rec[f]) if rec[f] is not None else "" for f in self.fields]

        while True:
            yield from (convert(rec) for rec in self.response["records"])
            if not self.response["done"]:
                self.response = self.sf.query_more(
                    self.response["nextRecordsUrl"], identifier_is_url=True
                )
            else:
                return


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

    def start(self):
        """Perform any required setup, such as job initialization, for the operation."""
        pass

    @abstractmethod
    def get_prev_record_values(self, records):
        """Get the previous records values in case of UPSERT and UPDATE to prepare for rollback"""
        pass

    @abstractmethod
    def select_records(self, records):
        """Perform the requested DML operation on the supplied row iterator."""
        pass

    @abstractmethod
    def load_records(self, records):
        """Perform the requested DML operation on the supplied row iterator."""
        pass

    def end(self):
        """Perform any required teardown for the operation before results are returned."""
        pass

    @abstractmethod
    def get_results(self):
        """Return a generator of DataOperationResult objects."""
        pass


class BulkApiDmlOperation(BaseDmlOperation, BulkJobMixin):
    """Operation class for all DML operations run using the Bulk API."""

    def __init__(
        self,
        *,
        sobject,
        operation,
        api_options,
        context,
        fields,
        selection_strategy=SelectStrategy.STANDARD,
        selection_filter=None,
        selection_priority_fields=None,
        content_type=None,
        threshold=None,
    ):
        super().__init__(
            sobject=sobject,
            operation=operation,
            api_options=api_options,
            context=context,
            fields=fields,
        )
        self.api_options = api_options.copy()
        self.api_options["batch_size"] = (
            self.api_options.get("batch_size") or DEFAULT_BULK_BATCH_SIZE
        )
        self.csv_buff = io.StringIO(newline="")
        self.csv_writer = csv.writer(self.csv_buff, quoting=csv.QUOTE_ALL)

        self.select_operation_executor = SelectOperationExecutor(selection_strategy)
        self.selection_filter = selection_filter
        self.weights = assign_weights(
            priority_fields=selection_priority_fields, fields=fields
        )
        self.content_type = content_type if content_type else "CSV"
        self.threshold = threshold

    def start(self):
        self.job_id = self.bulk.create_job(
            self.sobject,
            self.operation.value,
            contentType=self.content_type,
            concurrency=self.api_options.get("bulk_mode", "Parallel"),
            external_id_name=self.api_options.get("update_key"),
        )

    def end(self):
        self.bulk.close_job(self.job_id)
        if not self.job_result:
            self.job_result = self._wait_for_job(self.job_id)

    def get_prev_record_values(self, records):
        """Get the previous values of the records based on the update key
        to ensure rollback can be performed"""
        # Function to be called only for UPSERT and UPDATE
        assert self.operation in [DataOperationType.UPSERT, DataOperationType.UPDATE]

        self.logger.info(f"Retrieving Previous Record Values of {self.sobject}")
        prev_record_values = []
        relevant_fields = set(self.fields + ["Id"])

        # Set update key
        update_key = (
            self.api_options.get("update_key")
            if self.operation == DataOperationType.UPSERT
            else "Id"
        )

        for count, batch in enumerate(
            self._batch(records, self.api_options["batch_size"])
        ):
            self.context.logger.info(f"Querying batch {count + 1}")

            # Extract update key values from the batch
            update_key_values = [
                rec[update_key]
                for rec in csv.DictReader([line.decode("utf-8") for line in batch])
            ]

            # Construct the SOQL query
            query_fields = ", ".join(relevant_fields)
            query_values = ", ".join(f"'{value}'" for value in update_key_values)
            query = f"SELECT {query_fields} FROM {self.sobject} WHERE {update_key} IN ({query_values})"

            # Execute the query using Bulk API
            job_id = self.bulk.create_query_job(self.sobject, contentType="JSON")
            batch_id = self.bulk.query(job_id, query)
            self.bulk.wait_for_batch(job_id, batch_id)
            self.bulk.close_job(job_id)
            results = self.bulk.get_all_results_for_query_batch(batch_id)

            # Extract relevant fields from results and append to the respective lists
            for result in results:
                result = json.load(salesforce_bulk.util.IteratorBytesIO(result))
                prev_record_values.extend(
                    [[res[key] for key in relevant_fields] for res in result]
                )

        self.logger.info("Done")
        return prev_record_values, tuple(relevant_fields)

    def load_records(self, records):
        self.batch_ids = []

        batch_size = self.api_options["batch_size"]
        for count, csv_batch in enumerate(self._batch(records, batch_size)):
            self.context.logger.info(f"Uploading batch {count + 1}")
            self.batch_ids.append(self.bulk.post_batch(self.job_id, iter(csv_batch)))

    def select_records(self, records):
        """Executes a SOQL query to select records and adds them to results"""

        self.select_results = []  # Store selected records
        query_records = []
        # Create a copy of the generator using tee
        records, records_copy = tee(records)
        # Count total number of records to fetch using the copy
        total_num_records = sum(1 for _ in records_copy)

        # In the case that records are zero, return success
        if total_num_records == 0:
            self.logger.info(f"No records present for {self.sobject}")
            self.job_result = DataOperationJobResult(
                status=DataOperationStatus.SUCCESS,
                job_errors=[],
                records_processed=0,
                total_row_errors=0,
            )
            return

        limit_clause = self._determine_limit_clause(total_num_records=total_num_records)

        # Generate and execute SOQL query
        # (not passing offset as it is not supported in Bulk)
        (
            select_query,
            query_fields,
        ) = self.select_operation_executor.select_generate_query(
            sobject=self.sobject,
            fields=self.fields,
            user_filter=self.selection_filter if self.selection_filter else None,
            limit=limit_clause,
            offset=None,
        )

        # Execute the main select query using Bulk API
        self.logger.info("Retrieving records from org...")
        select_query_records = self._execute_select_query(
            select_query=select_query, query_fields=query_fields
        )
        self.logger.info(f"Retrieved {len(select_query_records)} from org")

        query_records.extend(select_query_records)
        # Post-process the query results
        (
            selected_records,
            insert_records,
            error_message,
        ) = self.select_operation_executor.select_post_process(
            load_records=records,
            query_records=query_records,
            fields=self.fields,
            num_records=total_num_records,
            sobject=self.sobject,
            weights=self.weights,
            threshold=self.threshold,
        )

        # Log the number of selected and prepared for insertion records
        num_selected = sum(1 for record in selected_records if record)
        num_prepared = len(insert_records) if insert_records else 0

        self.logger.info(
            f"{num_selected} records selected."
            + (
                f" {num_prepared} records prepared for insertion."
                if num_prepared > 0
                else ""
            )
        )

        if insert_records:
            self._process_insert_records(insert_records, selected_records)

        if not error_message:
            self.select_results.extend(selected_records)

        # Update job result based on selection outcome
        self.job_result = DataOperationJobResult(
            status=(
                DataOperationStatus.SUCCESS
                if len(self.select_results)
                else DataOperationStatus.JOB_FAILURE
            ),
            job_errors=[error_message] if error_message else [],
            records_processed=len(self.select_results),
            total_row_errors=0,
        )

    def _process_insert_records(self, insert_records, selected_records):
        """Processes and inserts records if necessary."""
        insert_fields, _ = split_and_filter_fields(fields=self.fields)
        insert_step = BulkApiDmlOperation(
            sobject=self.sobject,
            operation=DataOperationType.INSERT,
            api_options=self.api_options,
            context=self.context,
            fields=insert_fields,
        )
        insert_step.start()
        insert_step.load_records(insert_records)
        insert_step.end()
        # Retrieve insert results
        insert_results = []
        for batch_id in insert_step.batch_ids:
            try:
                results_url = f"{insert_step.bulk.endpoint}/job/{insert_step.job_id}/batch/{batch_id}/result"
                # Download entire result file to a temporary file first
                # to avoid the server dropping connections
                with download_file(results_url, insert_step.bulk) as f:
                    self.logger.info(f"Downloaded results for batch {batch_id}")
                    reader = csv.reader(f)
                    next(reader)  # Skip header row
                    for row in reader:
                        success = process_bool_arg(row[1])
                        created = process_bool_arg(row[2])
                        insert_results.append(
                            {"id": row[0], "success": success, "created": created}
                        )
            except Exception as e:
                raise BulkDataException(
                    f"Failed to download results for batch {batch_id} ({str(e)})"
                )

        insert_index = 0
        for idx, record in enumerate(selected_records):
            if record is None:
                selected_records[idx] = insert_results[insert_index]
                insert_index += 1

    def _determine_limit_clause(self, total_num_records):
        """Determines the LIMIT clause based on the retrieval mode."""
        if (
            self.select_operation_executor.retrieval_mode
            == SelectRecordRetrievalMode.ALL
        ):
            return None
        elif (
            self.select_operation_executor.retrieval_mode
            == SelectRecordRetrievalMode.MATCH
        ):
            return total_num_records

    def _execute_select_query(self, select_query: str, query_fields: List[str]):
        """Executes the select Bulk API query, retrieves results in JSON, and converts to CSV format if needed."""
        self.batch_id = self.bulk.query(self.job_id, select_query)
        self.bulk.wait_for_batch(self.job_id, self.batch_id)
        result_ids = self.bulk.get_query_batch_result_ids(
            self.batch_id, job_id=self.job_id
        )
        select_query_records = []

        for result_id in result_ids:
            # Modify URI to request JSON format
            uri = f"{self.bulk.endpoint}/job/{self.job_id}/batch/{self.batch_id}/result/{result_id}?format=json"
            # Download JSON data
            with download_file(uri, self.bulk) as f:
                data = json.load(f)
                # Get headers from fields, expanding nested structures for TYPEOF results
                self.headers = query_fields

                # Convert each record to a flat row
                for record in data:
                    flat_record = flatten_record(record, self.headers)
                    select_query_records.append(flat_record)

        return select_query_records

    def _batch(self, records, n, char_limit=10000000):
        """Given an iterator of records, yields batches of
        records serialized in .csv format.

        Batches adhere to the following, in order of precedence:
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
        """
        Retrieves and processes the results of a Bulk API operation.
        """

        if self.operation is DataOperationType.QUERY:
            yield from self._get_query_results()
        else:
            yield from self._get_batch_results()

    def _get_query_results(self):
        """Handles results for QUERY (select) operations"""
        for row in self.select_results:
            success = process_bool_arg(row["success"])
            created = process_bool_arg(row["created"])
            yield DataOperationResult(
                row["id"] if success else "",
                success,
                "",
                created,
            )

    def _get_batch_results(self):
        """Handles results for other DataOperationTypes (insert, update, etc.)"""
        for batch_id in self.batch_ids:
            try:
                results_url = (
                    f"{self.bulk.endpoint}/job/{self.job_id}/batch/{batch_id}/result"
                )
                # Download entire result file to a temporary file first
                # to avoid the server dropping connections
                with download_file(results_url, self.bulk) as f:
                    self.logger.info(f"Downloaded results for batch {batch_id}")
                    yield from self._parse_batch_results(f)

            except Exception as e:
                raise BulkDataException(
                    f"Failed to download results for batch {batch_id} ({str(e)})"
                )

    def _parse_batch_results(self, f):
        """Parses batch results from the downloaded file"""
        reader = csv.reader(f)
        next(reader)  # Skip header row

        for row in reader:
            success = process_bool_arg(row[1])
            created = process_bool_arg(row[2])
            yield DataOperationResult(
                row[0] if success else None,
                success,
                row[3] if not success else None,
                created,
            )


class RestApiDmlOperation(BaseDmlOperation):
    """Operation class for all DML operations run using the REST API."""

    def __init__(
        self,
        *,
        sobject,
        operation,
        api_options,
        context,
        fields,
        selection_strategy=SelectStrategy.STANDARD,
        selection_filter=None,
        selection_priority_fields=None,
        content_type=None,
        threshold=None,
    ):
        super().__init__(
            sobject=sobject,
            operation=operation,
            api_options=api_options,
            context=context,
            fields=fields,
        )

        # Because we send values in JSON, we must convert Booleans and nulls
        describe = {
            field["name"]: field
            for field in getattr(context.sf, sobject).describe()["fields"]
        }
        self.boolean_fields = [
            f for f in fields if "." not in f and describe[f]["type"] == "boolean"
        ]
        self.api_options = api_options.copy()
        self.api_options["batch_size"] = (
            self.api_options.get("batch_size") or DEFAULT_REST_BATCH_SIZE
        )
        self.api_options["batch_size"] = min(
            self.api_options["batch_size"], MAX_REST_BATCH_SIZE
        )

        self.select_operation_executor = SelectOperationExecutor(selection_strategy)
        self.selection_filter = selection_filter
        self.weights = assign_weights(
            priority_fields=selection_priority_fields, fields=fields
        )
        self.content_type = content_type
        self.threshold = threshold

    def _record_to_json(self, rec):
        result = dict(zip(self.fields, rec))
        for boolean_field in self.boolean_fields:
            try:
                result[boolean_field] = process_bool_arg(result[boolean_field] or False)
            except TypeError as e:
                raise BulkDataException(e)

        # Remove empty fields (different semantics in REST API)
        # We do this for insert only - on update, any fields set to `null`
        # are meant to be blanked out.
        if self.operation is DataOperationType.INSERT:
            result = {
                k: result[k]
                for k in result
                if result[k] is not None and result[k] != ""
            }
        elif self.operation in (DataOperationType.UPDATE, DataOperationType.UPSERT):
            result = {k: (result[k] if result[k] != "" else None) for k in result}

        result["attributes"] = {"type": self.sobject}
        return result

    def get_prev_record_values(self, records):
        """Get the previous values of the records based on the update key
        to ensure rollback can be performed"""
        # Function to be called only for UPSERT and UPDATE
        assert self.operation in [DataOperationType.UPSERT, DataOperationType.UPDATE]

        self.logger.info(f"Retrieving Previous Record Values of {self.sobject}")
        prev_record_values = []
        relevant_fields = set(self.fields + ["Id"])

        # Set update key
        update_key = (
            self.api_options.get("update_key")
            if self.operation == DataOperationType.UPSERT
            else "Id"
        )

        for chunk in iterate_in_chunks(self.api_options.get("batch_size"), records):
            update_key_values = tuple(
                filter(None, (self._record_to_json(rec)[update_key] for rec in chunk))
            )

            # Construct the query string
            query_fields = ", ".join(relevant_fields)
            query = f"SELECT {query_fields} FROM {self.sobject} WHERE {update_key} IN {update_key_values}"

            # Execute the query
            results = self.sf.query(query)

            # Extract relevant fields from results and extend the list
            prev_record_values.extend(
                [[res[key] for key in relevant_fields] for res in results["records"]]
            )

        self.logger.info("Done")
        return prev_record_values, tuple(relevant_fields)

    def load_records(self, records):
        """Load, update, upsert or delete records into the org"""

        self.results = []
        method = {
            DataOperationType.INSERT: "POST",
            DataOperationType.UPDATE: "PATCH",
            DataOperationType.DELETE: "DELETE",
            DataOperationType.UPSERT: "PATCH",
        }[self.operation]

        update_key = self.api_options.get("update_key")
        for chunk in iterate_in_chunks(self.api_options.get("batch_size"), records):
            if self.operation is DataOperationType.DELETE:
                url_string = "?ids=" + ",".join(
                    self._record_to_json(rec)["Id"] for rec in chunk
                )
                json = None
            else:
                if update_key:
                    assert self.operation == DataOperationType.UPSERT
                    url_string = f"/{self.sobject}/{update_key}"
                else:
                    url_string = ""
                json = {
                    "allOrNone": False,
                    "records": [self._record_to_json(rec) for rec in chunk],
                }

            self.results.extend(
                self.sf.restful(
                    f"composite/sobjects{url_string}", method=method, json=json
                )
            )

        row_errors = len([res for res in self.results if not res["success"]])
        self.job_result = DataOperationJobResult(
            (
                DataOperationStatus.SUCCESS
                if not row_errors
                else DataOperationStatus.ROW_FAILURE
            ),
            [],
            len(self.results),
            row_errors,
        )

    def select_records(self, records):
        """Executes a SOQL query to select records and adds them to results"""

        self.results = []
        query_records = []

        # Create a copy of the generator using tee
        records, records_copy = tee(records)

        # Count total number of records to fetch using the copy
        total_num_records = sum(1 for _ in records_copy)

        # In the case that records are zero, return success
        self.logger.info(f"No records present for {self.sobject}")
        if total_num_records == 0:
            self.job_result = DataOperationJobResult(
                status=DataOperationStatus.SUCCESS,
                job_errors=[],
                records_processed=0,
                total_row_errors=0,
            )
            return

        # Set LIMIT condition
        limit_clause = self._determine_limit_clause(total_num_records)

        # Generate the SOQL query based on the selection strategy
        (
            select_query,
            query_fields,
        ) = self.select_operation_executor.select_generate_query(
            sobject=self.sobject,
            fields=self.fields,
            user_filter=self.selection_filter or None,
            limit=limit_clause,
            offset=None,
        )

        # Execute the query and gather the records
        self.logger.info("Retrieving records from org...")
        query_records = self._execute_soql_query(select_query, query_fields)
        self.logger.info(f"Retrieved {len(query_records)} from org")

        # Post-process the query results for this batch
        (
            selected_records,
            insert_records,
            error_message,
        ) = self.select_operation_executor.select_post_process(
            load_records=records,
            query_records=query_records,
            fields=self.fields,
            num_records=total_num_records,
            sobject=self.sobject,
            weights=self.weights,
            threshold=self.threshold,
        )

        # Log the number of selected and prepared for insertion records
        num_selected = sum(1 for record in selected_records if record)
        num_prepared = len(insert_records) if insert_records else 0

        self.logger.info(
            f"{num_selected} records selected."
            + (
                f" {num_prepared} records prepared for insertion."
                if num_prepared > 0
                else ""
            )
        )

        if insert_records:
            self._process_insert_records(insert_records, selected_records)

        if not error_message:
            # Add selected records from this batch to the overall results
            self.results.extend(selected_records)

        # Update the job result based on the overall selection outcome
        self._update_job_result(error_message)

    def _determine_limit_clause(self, total_num_records):
        """Determines the LIMIT clause based on the retrieval mode."""
        if (
            self.select_operation_executor.retrieval_mode
            == SelectRecordRetrievalMode.ALL
        ):
            return None
        elif (
            self.select_operation_executor.retrieval_mode
            == SelectRecordRetrievalMode.MATCH
        ):
            return total_num_records

    def _execute_soql_query(self, select_query, query_fields):
        """Executes the SOQL query and returns the flattened records."""
        query_records = []
        response = self.sf.restful(f"query/?q={quote(select_query)}", method="GET")
        query_records.extend(self._flatten_response_records(response, query_fields))

        while not response["done"]:
            response = self.sf.query_more(
                response["nextRecordsUrl"], identifier_is_url=True
            )
            query_records.extend(self._flatten_response_records(response, query_fields))

        return query_records

    def _flatten_response_records(self, response, query_fields):
        """Flattens the response records and returns them as a list."""
        return [flatten_record(record, query_fields) for record in response["records"]]

    def _process_insert_records(self, insert_records, selected_records):
        """Processes and inserts records if necessary."""
        insert_fields, _ = split_and_filter_fields(fields=self.fields)
        insert_step = RestApiDmlOperation(
            sobject=self.sobject,
            operation=DataOperationType.INSERT,
            api_options=self.api_options,
            context=self.context,
            fields=insert_fields,
        )
        insert_step.start()
        insert_step.load_records(insert_records)
        insert_step.end()
        insert_results = insert_step.results

        insert_index = 0
        for idx, record in enumerate(selected_records):
            if record is None:
                selected_records[idx] = insert_results[insert_index]
                insert_index += 1

    def _update_job_result(self, error_message):
        """Updates the job result based on the selection outcome."""
        self.job_result = DataOperationJobResult(
            status=(
                DataOperationStatus.SUCCESS
                if len(self.results)
                else DataOperationStatus.JOB_FAILURE
            ),
            job_errors=[error_message] if error_message else [],
            records_processed=len(self.results),
            total_row_errors=0,
        )

    def get_results(self):
        """Return a generator of DataOperationResult objects."""

        def _convert(res):
            # TODO: make DataOperationResult handle this error variant
            if res.get("errors"):
                errors = "\n".join(
                    f"{e['statusCode']}: {e['message']} ({','.join(e['fields'])})"
                    for e in res["errors"]
                )
            else:
                errors = ""

            if self.operation == DataOperationType.INSERT:
                created = True
            elif self.operation == DataOperationType.UPDATE:
                created = False
            else:
                created = res.get("created")

            return DataOperationResult(res.get("id"), res["success"], errors, created)

        yield from (_convert(res) for res in self.results)


def get_query_operation(
    *,
    sobject: str,
    fields: List[str],
    api_options: Dict,
    context: Any,
    query: str,
    api: Optional[DataApi] = DataApi.SMART,
) -> BaseQueryOperation:
    """Create an appropriate QueryOperation instance for the given parameters, selecting
    between REST and Bulk APIs based upon volume (Bulk > 2000 records) if DataApi.SMART
    is provided."""

    # The Record Count endpoint requires API 40.0. REST Collections requires 42.0.
    api_version = float(context.sf.sf_version)
    if api_version < 42.0 and api is not DataApi.BULK:
        api = DataApi.BULK

    if api in (DataApi.SMART, None):
        record_count_response = context.sf.restful(
            f"limits/recordCount?sObjects={sobject}"
        )
        sobject_map = {
            entry["name"]: entry["count"] for entry in record_count_response["sObjects"]
        }
        api = (
            DataApi.BULK
            if sobject in sobject_map and sobject_map[sobject] >= 2000
            else DataApi.REST
        )

    if api is DataApi.BULK:
        return BulkApiQueryOperation(
            sobject=sobject, api_options=api_options, context=context, query=query
        )
    elif api is DataApi.REST:
        return RestApiQueryOperation(
            sobject=sobject,
            api_options=api_options,
            context=context,
            query=query,
            fields=fields,
        )
    else:
        raise AssertionError(f"Unknown API: {api}")


def get_dml_operation(
    *,
    sobject: str,
    operation: DataOperationType,
    fields: List[str],
    api_options: Dict,
    context: Any,
    volume: int,
    api: Optional[DataApi] = DataApi.SMART,
    selection_strategy: SelectStrategy = SelectStrategy.STANDARD,
    selection_filter: Union[str, None] = None,
    selection_priority_fields: Union[dict, None] = None,
    content_type: Union[str, None] = None,
    threshold: Union[float, None] = None,
) -> BaseDmlOperation:
    """Create an appropriate DmlOperation instance for the given parameters, selecting
    between REST and Bulk APIs based upon volume (Bulk used at volumes over 2000 records,
    or if the operation is HARD_DELETE, which is only available for Bulk)."""

    context.logger.debug(f"Creating {operation} Operation for {sobject} using {api}")
    assert isinstance(operation, DataOperationType)

    # REST Collections requires 42.0.
    api_version = float(context.sf.sf_version)
    if api_version < 42.0 and api is not DataApi.BULK:
        api = DataApi.BULK

    if api in (DataApi.SMART, None):
        api = (
            DataApi.BULK
            if volume >= 2000 or operation is DataOperationType.HARD_DELETE
            else DataApi.REST
        )

    if api is DataApi.BULK:
        api_class = BulkApiDmlOperation
    elif api is DataApi.REST:
        api_class = RestApiDmlOperation
    else:
        raise AssertionError(f"Unknown API: {api}")

    return api_class(
        sobject=sobject,
        operation=operation,
        api_options=api_options,
        context=context,
        fields=fields,
        selection_strategy=selection_strategy,
        selection_filter=selection_filter,
        selection_priority_fields=selection_priority_fields,
        content_type=content_type,
        threshold=threshold,
    )


def extract_flattened_headers(query_fields):
    """Extract headers from query fields, including handling of TYPEOF fields."""
    headers = []

    for field in query_fields:
        if isinstance(field, dict):
            # Handle TYPEOF / polymorphic fields
            for lookup, references in field.items():
                # Assuming each reference is a list of dictionaries
                for ref_type in references:
                    for ref_obj, ref_fields in ref_type.items():
                        for nested_field in ref_fields:
                            headers.append(
                                f"{lookup}.{ref_obj}.{nested_field}"
                            )  # Flatten the structure
        else:
            # Regular fields
            headers.append(field)

    return headers


def flatten_record(record, headers):
    """Flatten each record to match headers, handling nested fields."""
    flat_record = []

    for field in headers:
        components = field.split(".")
        value = ""

        # Handle lookup fields with two or three components
        if len(components) >= 2:
            lookup_field = components[0]
            lookup = record.get(lookup_field, None)

            # Check if lookup field exists in the record
            if lookup is None:
                value = ""
            else:
                if len(components) == 2:
                    # Handle fields with two components: {lookup}.{ref_field}
                    ref_field = components[1]
                    value = lookup.get(ref_field, "")
                elif len(components) == 3:
                    # Handle fields with three components: {lookup}.{ref_obj}.{ref_field}
                    ref_obj, ref_field = components[1], components[2]
                    # Check if the type matches the specified ref_obj
                    if lookup.get("attributes", {}).get("type") == ref_obj:
                        value = lookup.get(ref_field, "")
                    else:
                        value = ""

        else:
            # Regular fields or non-polymorphic fields
            value = record.get(field, "")

        # Set None values to empty string
        if value is None:
            value = ""
        elif not isinstance(value, str):
            value = str(value)

        # Append the resolved value to the flattened record
        flat_record.append(value)

    return flat_record


def assign_weights(
    priority_fields: Union[Dict[str, str], None], fields: List[str]
) -> list:
    # If priority_fields is None or an empty dictionary, set all weights to 1
    if not priority_fields:
        return [1] * len(fields)

    # Initialize the weight list with LOW_PRIORITY_VALUE
    weights = [LOW_PRIORITY_VALUE] * len(fields)

    # Iterate over the fields and assign weights based on priority_fields
    for i, field in enumerate(fields):
        if field in priority_fields:
            # Set weight to HIGH_PRIORITY_VALUE if field is in priority_fields
            weights[i] = HIGH_PRIORITY_VALUE

    return weights
