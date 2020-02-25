""" a task for waiting on a Batch Apex job to complete """
from datetime import datetime
from typing import Sequence, Optional

from cumulusci.utils import parse_api_datetime
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import SalesforceException

COMPLETED_STATUSES = ["Completed"]


class BatchApexWait(BaseSalesforceApiTask):
    """ BatchApexWait polls an org until the latest batch job
        for an apex class completes or fails."""

    name = "BatchApexWait"
    original_created_date = None

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

        summary = self.summarize_batches(self.batches)
        failed_batches = self.failed_batches(self.batches)

        if failed_batches:
            self.logger.info("There have been some batch failures.")
            self.logger.info("Error values:")
            self.logger.info(repr(failed_batches))
            raise SalesforceException(
                f"There were batch errors: {repr(failed_batches)}"
            )
        elif not summary["CountsAddUp"]:
            self.logger.info("The final record counts do not add up.")
            self.logger.info("This is probably related to W-1132237")
            self.logger.info(repr(summary))

        self.logger.info(
            f"{self.options['class_name']} took {summary['ElapsedTime']} seconds to process {summary['TotalJobItems']} batches."
        )

    def failed_batches(self, batches: Sequence[dict]):
        failed_batches = []
        for batch in batches:
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
            query_results = self.tooling.query(self._batch_query(date_limit=None))
            self.original_created_date = parse_api_datetime(
                query_results["records"][0]["CreatedDate"]
            )
        else:
            query_results = self.tooling.query(
                self._batch_query(date_limit=self.original_created_date)
            )

        self.batches = query_results["records"]
        current_batch = self.batches[0]

        summary = self.summarize_batches(self.batches)
        self.logger.info(
            f"{self.options['class_name']}: "
            f"Job{'s' if len(summary['Jobs'])>1 else ''}: {summary['Jobs']}"
            f"{summary['JobItemsProcessed']} of {summary['TotalJobItems']} "
            f"({summary['NumberOfErrors']} failures)"
        )

        self.poll_complete = current_batch["Status"] in COMPLETED_STATUSES

    def summarize_batches(self, batches: Sequence[dict]):
        def reduce_key(valname: str, summary_func):
            return summary_func(batch[valname] for batch in batches)

        rc = {
            "Jobs": reduce_key("Id", ",".join),
            "JobItemsProcessed": reduce_key("JobItemsProcessed", sum),
            "TotalJobItems": reduce_key("TotalJobItems", sum),
            "NumberOfErrors": reduce_key("NumberOfErrors", sum),
        }
        rc["Success"] = rc["NumberOfErrors"] == 0
        rc["ElapsedTime"] = self.delta(batches)
        rc["CountsAddUp"] = (rc["JobItemsProcessed"] == rc["TotalJobItems"]) and (
            rc["NumberOfErrors"] == 0
        )
        return rc

    def delta(self, batches: Sequence[dict]):
        """ returns the time (in seconds) that the batches took, if complete """
        most_recently_completed = max(batch["CompletedDate"] for batch in batches)
        if most_recently_completed:
            completed_date = parse_api_datetime(most_recently_completed)
        else:
            completed_date = datetime.now()
        created_date = parse_api_datetime(
            min(batch["CreatedDate"] for batch in batches)
        )
        td = completed_date - created_date
        return td.total_seconds()

    def _batch_query(self, date_limit: Optional[datetime] = None):
        if not date_limit:
            limit = " LIMIT 1 "
            date_clause = "  "
        else:
            limit = " "
            date_clause = f" AND CreatedDate >= {date_limit.isoformat()}Z "

        query = (
            "SELECT Id, ApexClass.Name, Status, ExtendedStatus, TotalJobItems, "
            "JobItemsProcessed, NumberOfErrors, CreatedDate, CompletedDate "
            "FROM AsyncApexJob "
            "WHERE JobType='BatchApex' "
            + f"AND ApexClass.Name='{self.options['class_name']}' "
            + date_clause
            + " ORDER BY CreatedDate DESC "
            + limit
        )
        return query
