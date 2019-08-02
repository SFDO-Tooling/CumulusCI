import requests
import time
import unicodecsv
import xml.etree.ElementTree as ET

from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.bulkdata.utils import BulkJobTaskMixin
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


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
