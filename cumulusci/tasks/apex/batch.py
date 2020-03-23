""" a task for waiting on a Batch Apex job to complete """
from datetime import datetime
from typing import Sequence, Optional

from cumulusci.utils import parse_api_datetime
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import SalesforceException

COMPLETED_STATUSES = ["Completed", "Aborted", "Failed"]
STOPPED_STATUSES = ["Aborted"]
FAILED_STATUSES = ["Failed"]


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

        summary = self.summarize_subjobs(self.subjobs)
        failed_batches = self.failed_batches(self.subjobs)
        job_aborted = summary["AnyAborted"]
        job_failed = summary[
            "AnyFailed"
        ]  # note that a failed sub-job is different than a failed batch

        # per https://help.salesforce.com/articleView?id=code_apex_job.htm&type=5
        if job_aborted:
            raise SalesforceException("Job was aborted by a user.")
        elif job_failed:
            raise SalesforceException("Job experienced a system failure.")
        elif failed_batches:
            self.logger.info("There have been some batch failures.")
            raise SalesforceException(
                f"There were batch errors: {repr(failed_batches)}"
            )
        elif not summary["CountsAddUp"]:
            self.logger.info("The final record counts do not add up.")
            self.logger.info("This is probably related to W-1132237")
            self.logger.info(repr(summary))

        if len(self.subjobs) > 1:
            subjob_summary = f" in {len(self.subjobs)} sub-jobs"
        else:
            subjob_summary = ""

        self.logger.info(
            f"{self.options['class_name']} took {summary['ElapsedTime']} seconds to process {summary['TotalJobItems']} batches{subjob_summary}."
        )

    def failed_batches(self, subjobs: Sequence[dict]):
        failed_batches = []
        for subjob in subjobs:
            if subjob["NumberOfErrors"]:
                failed_batches.append(
                    {
                        key: value
                        for key, value in subjob.items()
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
            if not query_results["records"]:
                raise SalesforceException(f"No {self.options['class_name']} job found.")
            self.original_created_date = parse_api_datetime(
                query_results["records"][0]["CreatedDate"]
            )
        else:
            query_results = self.tooling.query(
                self._batch_query(date_limit=self.original_created_date)
            )

        self.subjobs = query_results["records"]
        current_subjob = self.subjobs[0]

        summary = self.summarize_subjobs(self.subjobs)

        if len(self.subjobs) > 1:
            subjob_info = f" in {len(self.subjobs)} sub-jobs."
        else:
            subjob_info = ""

        self.logger.info(
            f"{self.options['class_name']}: "
            f"Job: {current_subjob['Id']} "
            f"{summary['JobItemsProcessed']} of {summary['TotalJobItems']} "
            f"({summary['NumberOfErrors']} failures)" + subjob_info
        )

        self.poll_complete = summary["Completed"]

    def summarize_subjobs(self, subjobs: Sequence[dict]):
        def reduce_key(valname: str, summary_func):
            return summary_func(subjob[valname] for subjob in subjobs)

        rc = {
            "JobItemsProcessed": reduce_key("JobItemsProcessed", sum),
            "TotalJobItems": reduce_key("TotalJobItems", sum),
            "NumberOfErrors": reduce_key("NumberOfErrors", sum),
            "Completed": all(
                subjob["Status"] in COMPLETED_STATUSES for subjob in subjobs
            ),
            "AnyAborted": any(
                subjob["Status"] in STOPPED_STATUSES for subjob in subjobs
            ),
            "AnyFailed": any(subjob["Status"] in FAILED_STATUSES for subjob in subjobs),
        }
        rc["Success"] = rc["NumberOfErrors"] == 0
        rc["ElapsedTime"] = self.elapsed_time(subjobs)
        rc["CountsAddUp"] = rc["JobItemsProcessed"] == rc["TotalJobItems"]
        return rc

    def elapsed_time(self, subjobs: Sequence[dict]):
        """ returns the time (in seconds) that the subjobs took, if complete """
        completed_dates = [
            subjob["CompletedDate"] for subjob in subjobs if subjob.get("CompletedDate")
        ]
        if completed_dates:
            most_recently_completed = max(completed_dates)
            completed_date = parse_api_datetime(most_recently_completed)
        else:
            completed_date = datetime.now()
        created_date = parse_api_datetime(
            min(subjob["CreatedDate"] for subjob in subjobs)
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
