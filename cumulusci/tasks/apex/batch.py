""" a task for waiting on a Batch Apex job to complete """

from cumulusci.utils import parse_api_datetime
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import SalesforceException

COMPLETED_STATUSES = ["Completed"]


class BatchApexWait(BaseSalesforceApiTask):
    """ BatchApexWait polls an org until the latest batch job
        for an apex class completes or fails """

    name = "BatchApexWait"
    batch = object()

    task_options = {
        "class_name": {
            "description": "Name of the Apex class to wait for.",
            "required": True,
        },
        "poll_interval": {
            "description": "Seconds to wait before polling for batch job completion. "
            "Defaults to 10 seconds."
        },
    }

    def _run_task(self):
        self.poll_interval_s = int(self.options.get("poll_interval", 10))

        self._poll()  # will block until poll_complete

        self.logger.info("Job is complete.")

        vals = {
            key: value
            for key, value in self.batch.items()
            if key
            in {
                "Id",
                "Status",
                "ExtendedStatus",
                "NumberOfErrors",
                "JobItemsProcessed",
                "TotalJobItems",
            }
        }
        if not self.success:
            self.logger.info("There have been some batch failures.")
            self.logger.info("Error values:")
            self.logger.info(repr(vals))
            raise SalesforceException("There were import errors: %s" % repr(vals))
        elif not self.done_for_sure:
            self.logger.info("The final record counts do not add up.")
            self.logger.info("This is probably related to W-1132237")
            self.logger.info(repr(vals))

        self.logger.info(
            "%s took %d seconds to process %d batches.",
            self.batch["ApexClass"]["Name"],
            self.delta,
            self.batch["TotalJobItems"],
        )

        return self.success

    def _poll_action(self):
        # get batch status
        query_results = self.tooling.query(self._batch_query)

        self.batch = query_results["records"][0]
        self.logger.info(
            "%s: %d of %d (%d failures)",
            self.batch["ApexClass"]["Name"],
            self.batch["JobItemsProcessed"],
            self.batch["TotalJobItems"],
            self.batch["NumberOfErrors"],
        )

        self.poll_complete = not self._poll_again()

    def _poll_again(self):
        return self.batch["Status"] not in COMPLETED_STATUSES

    @property
    def success(self):
        return self.batch["NumberOfErrors"] == 0

    @property
    def done_for_sure(self):
        """ returns True if all batches were counted and succeeded """
        return (self.batch["JobItemsProcessed"] == self.batch["TotalJobItems"]) and (
            self.batch["NumberOfErrors"] == 0
        )

    @property
    def delta(self):
        """ returns the time (in seconds) that the batch took, if complete """
        completed_date = parse_api_datetime(self.batch["CompletedDate"])
        created_date = parse_api_datetime(self.batch["CreatedDate"])
        td = completed_date - created_date
        return td.total_seconds()

    @property
    def _batch_query(self):
        return (
            "SELECT Id, ApexClass.Name, Status, ExtendedStatus, TotalJobItems, "
            "JobItemsProcessed, NumberOfErrors, CreatedDate, CompletedDate "
            "FROM AsyncApexJob "
            "WHERE JobType='BatchApex' "
            "AND ApexClass.Name='{}' "
            "ORDER BY CreatedDate DESC "
            "LIMIT 1".format(self.options["class_name"])
        )
