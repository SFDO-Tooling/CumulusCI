import csv
import io
import itertools
from collections import namedtuple
from enum import Enum
from cumulusci.tasks.bulkdata.utils import BulkJobTaskMixin, download_file
from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class Operation(Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    HARD_DELETE = "hardDelete"
    QUERY = "query"


class Api(Enum):
    BULK = "bulk"
    REST = "rest"


class Status(Enum):
    SUCCESS = "Succeeded"
    FAILURE = "Failed"
    PARTIAL_SUCCESS = "PartialSuccess"


Result = namedtuple("Result", ["id", "error"])


def BatchIterator(iterator, n=10000):
    while True:
        batch = list(itertools.islice(iterator, n))
        if not batch:
            return

        yield batch


class Step:
    def __init__(
        self,
        sobject: str,
        operation: Operation,
        api_options: dict,
        context: BaseSalesforceApiTask,
    ):
        self.sobject = sobject
        self.operation = operation
        self.api_options = api_options
        self.context = context
        self.status = None


class QueryStep(Step):
    def __init__(
        self,
        sobject: str,
        api_options: dict,
        context: BaseSalesforceApiTask,
        query: str,
    ):
        super().__init__(sobject, Operation.QUERY, api_options, context)
        self.query = query

    def query(self):
        pass

    def get_results(self):
        pass


class BulkApiQueryStep(QueryStep, BulkJobTaskMixin):
    def query(self):
        self.job_id = self.context.bulk.create_query_job(
            self.sobject, contentType="CSV"
        )
        self.batch_id = self.context.bulk.query(self.job_id, self.query)
        self.bulk.wait_for_batch(self.job_id, self.batch_id)
        self.bulk.close_job(self.job_id)

    def get_results(self):
        result_ids = self.context.bulk.get_query_batch_result_ids(
            self.batch_id, job_id=self.job_id
        )
        for result_id in result_ids:
            uri = f"{self.context.bulk.endpoint}/job/{self.job_id}/batch/{self.batch_id}/result/{result_id}"
            with download_file(uri, self.context.bulk) as f:
                reader = csv.reader(f)
                self.headers = next(reader)
                if "Records not found for this query" in self.headers:
                    raise StopIteration

                yield from reader


class DmlStep(Step):
    def __init__(
        self,
        sobject: str,
        operation: Operation,
        api_options: dict,
        context: BaseSalesforceApiTask,
        fields,
    ):
        super().__init__(sobject, operation, api_options, context)
        self.fields = fields

    def start(self):
        pass

    def load_records(self, records):
        pass

    def end(self):
        pass

    def get_results(self):
        return []


class BulkApiDmlStep(DmlStep, BulkJobTaskMixin):
    def start(self):
        if self.operation is Operation.INSERT:
            self.job_id = self.context.bulk.create_insert_job(
                self.sobject, contentType="CSV"
            )
        else:
            self.job_id = self.context.create_update_job(
                self.sobject, contentType="CSV"
            )

    def load_records(self, records):
        self.batch_ids = []

        for batch_file in self._batch(records):
            self.batch_ids.append(self.context.bulk.post_batch(self.job_id, batch_file))

    def _batch(self, records):
        for batch in BatchIterator(records, self.api_options.get("batch_size", 10000)):
            batch_file = io.BytesIO()
            writer = csv.writer(batch_file)

            writer.writerow(self.fields)
            for record in batch:
                writer.writerow(record)

            batch_file.seek(0)
            yield batch_file

    def end(self):
        self.bulk.close_job(self.job_id)
        result = self._wait_for_job(self.job_id)
        if result == "Completed":
            self.status = Status.SUCCESS
        else:
            self.status = Status.FAILURE

    def get_new_ids(self):
        for batch_id in self.batch_ids:
            try:
                results_url = f"{self.context.bulk.endpoint}/job/{self.job_id}/batch/{batch_id}/result"
                # Download entire result file to a temporary file first
                # to avoid the server dropping connections
                with download_file(results_url, self.bulk) as f:
                    self.logger.info(f"  Downloaded results for batch {batch_id}")

                    reader = csv.reader(f)
                    next(reader)  # skip header

                    for row in reader:
                        yield Result(
                            row[0] if row[1] == "true" else None,
                            row[3] if row[1] != "true" else None,
                        )
            except Exception as e:
                raise BulkDataException(
                    f"Failed to download results for batch {batch_id} ({str(e)})"
                )
