import requests
import time
import unicodecsv
import xml.etree.ElementTree as ET

from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.bulkdata.utils import BulkJobTaskMixin
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import TaskOptionsError


class DeleteData(BaseSalesforceApiTask, BulkJobTaskMixin):
    task_options = {
        "objects": {
            "description": "A list of objects to delete records from in order of deletion.  If passed via command line, use a comma separated string",
            "required": True,
        },
        "where": {
            "description": "A SOQL where-clause (without the keyword WHERE). Only available when 'objects' is length 1.",
            "required": False,
        },
        "hardDelete": {
            "description": "If True, perform a hard delete, bypassing the recycle bin. Default: False"
        },
    }

    def _init_options(self, kwargs):
        super(DeleteData, self)._init_options(kwargs)

        # Split and trim objects string into a list if not already a list
        self.options["objects"] = process_list_arg(self.options["objects"])
        if not len(self.options["objects"]) or not self.options["objects"][0]:
            raise TaskOptionsError("At least one object must be specified.")

        self.options["where"] = self.options.get("where", None)
        if len(self.options["objects"]) > 1 and self.options["where"]:
            raise TaskOptionsError(
                "Criteria cannot be specified if more than one object is specified."
            )
        self.options["hardDelete"] = process_bool_arg(self.options.get("hardDelete"))

    def _run_task(self):
        for obj in self.options["objects"]:
            self.logger.info(f"Deleting {self._object_description(obj)} ")
            delete_job = self._create_job(obj, self.options["where"])
            if delete_job is not None:
                self._wait_for_job(delete_job)

    def _create_job(self, obj, where=None):
        # Query for rows to delete
        delete_rows = self._query_salesforce_for_records_to_delete(obj, where)
        if not delete_rows:
            self.logger.info(f"  No {obj} objects found, skipping delete")
            return

        # Upload all the batches
        operation = "hardDelete" if self.options["hardDelete"] else "delete"
        delete_job = self.bulk.create_job(obj, operation)
        self.logger.info(f"  Deleting {len(delete_rows)} {obj} records")
        batch_num = 1
        for batch in self._upload_batches(delete_job, delete_rows):
            self.logger.info(f"    Uploaded batch {batch}")
            batch_num += 1
        self.bulk.close_job(delete_job)
        return delete_job

    def compose_query(self, obj, where):
        query = f"SELECT Id FROM {obj}"
        if where:
            query += f" WHERE {where}"

        return query

    def _object_description(self, obj):
        if self.options["where"]:
            return f'{obj} objects matching "{self.options["where"]}"'
        else:
            return f"all {obj} objects"

    def _query_salesforce_for_records_to_delete(self, obj, where):
        # Query for all record ids
        self.logger.info(f"  Querying for {self._object_description(obj)}")
        query_job = self.bulk.create_query_job(obj, contentType="CSV")
        batch = self.bulk.query(query_job, self.compose_query(obj, where))
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
        uri = f"{self.bulk.endpoint}/job/{job}/batch"
        headers = self.bulk.headers({"Content-Type": "text/csv"})
        for batch in self._split_batches(data, 10000):
            rows = ['"Id"']
            rows += [f'"{record["Id"]}"' for record in batch]
            resp = requests.post(uri, data="\n".join(rows), headers=headers)
            content = resp.content
            if resp.status_code >= 400:
                self.bulk.raise_error(content, resp.status_code)

            tree = ET.fromstring(content)
            batch_id = tree.findtext("{%s}id" % self.bulk.jobNS)

            yield batch_id
