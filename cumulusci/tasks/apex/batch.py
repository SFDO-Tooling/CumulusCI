""" a task for waiting on a Batch Apex job to complete """

from cumulusci.utils import parse_api_datetime
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import SalesforceException

COMPLETED_STATUSES = ["Completed"]


class BatchApexWait(BaseSalesforceApiTask):
    """ BatchApexWait polls an org until the latest batch job
        for an apex class completes or fails """

    name = "BatchApexWait"

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

        summary = self.summarize_batches()
        failed_batches = self.failed_batches()

        if failed_batches:
            self.logger.info("There have been some batch failures.")
            self.logger.info("Error values:")
            self.logger.info(repr(failed_batches))
            raise SalesforceException(
                f"There were import errors: {repr(failed_batches)}"
            )
        elif not self.done_for_sure(self.batches):
            self.logger.info("The final record counts do not add up.")
            self.logger.info("This is probably related to W-1132237")
            self.logger.info(repr(summary))

        self.logger.info(
            f"{summary['Name']} took {self.delta(self.batches)} seconds to process {summary['TotalJobItems']} batches."
        )

        return self.success

    def failed_batches(self, batches):
        failed_batches = []
        for batch in batches.values():
            if batch["NumberOfErrors"]:
                failed_batches.append(
                    {
                        key: value
                        for key, value in batch.items()
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
                )
        return failed_batches

    def _poll_action(self):
        # get batch status

        if not self.original_created_date:
            query_results = self.tooling.query(self._batch_query(first_time=True))
            self.original_created_date = "FIXME"  # TODO
        else:
            query_results = self.tooling.query(self._batch_query(first_time=False))

        self.batches = query_results["records"]
        current_batch = self.batches[0]

        summary = self.summarize_batches(self.batches)
        self.logger.info(
            f"{summary['Name']}: "
            f"{summary['JobItemsProcessed']} of {summary['TotalJobItems']} "
            f"({summary['NumberOfErrors']} failures)"
        )

        self.poll_complete = current_batch["Status"] in COMPLETED_STATUSES

    def summarize_batches(self, batches):
        def sum_val(valname: str):
            return sum(batch[valname] for batch in batches.values())

        return {
            "JobItemsProcessed": sum_val("JobItemsProcessed"),
            "TotalJobItems": sum_val("TotalJobItems"),
            "NumberOfErrors": sum_val("NumberOfErrors"),
        }

    def success(self, batches):
        return self.summarize_batches(batches)["NumberOfErrors"] == 0

    def done_for_sure(self, batches):
        """ returns True if all batches were counted and succeeded """
        summary = self.summarize_batches()
        return (summary["JobItemsProcessed"] == summary["TotalJobItems"]) and (
            summary["NumberOfErrors"] == 0
        )

    def delta(self, batches):
        """ returns the time (in seconds) that the batches took, if complete """
        batches = list(batches.values())
        completed_date = parse_api_datetime(batches[-1]["CompletedDate"])
        created_date = parse_api_datetime(batches[0]["CreatedDate"])
        td = completed_date - created_date
        return td.total_seconds()

    def _batch_query(self, first_time=False):
        if first_time:
            limit = " LIMIT 1 "
            date_clause = "  "
        else:
            limit = " "
            assert self.original_created_data
            date_clause = f" AND CreatedDate DESC > {self.original_created_date} "

        return (
            "SELECT Id, ApexClass.Name, Status, ExtendedStatus, TotalJobItems, "
            "JobItemsProcessed, NumberOfErrors, CreatedDate, CompletedDate "
            "FROM AsyncApexJob "
            "WHERE JobType='BatchApex' "
            + f"AND ApexClass.Name='{self.options['class_name']}' "
            + date_clause
            + " ORDER BY CreatedDate DESC "
            + limit
        )
