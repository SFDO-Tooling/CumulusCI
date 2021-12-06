""" simple task(s) for reporting on push upgrade jobs.

this doesn't use the nearby push_api module, and was just a quick ccistyle
get the job done kinda moment.
"""

import csv
import re

from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class ReportPushFailures(BaseSalesforceApiTask):
    """Produce a report of the failed and otherwise anomalous push jobs.

    Takes a push request id and writes results to a CSV file. The task result contains the filename."""

    task_doc = __doc__
    task_options = {
        "request_id": {
            "description": "PackagePushRequest ID for the request you need to report on.",
            "required": True,
        },
        "result_file": {
            "description": "Path to write a CSV file with the results. Defaults to 'push_fails.csv'."
        },
        "ignore_errors": {
            "description": "List of ErrorTitle and ErrorType values to omit from the report"
        },
    }
    api_version = "43.0"
    job_query = "SELECT ID, SubscriberOrganizationKey, (SELECT ErrorDetails, ErrorMessage, ErrorSeverity, ErrorTitle, ErrorType FROM PackagePushErrors) FROM PackagePushJob WHERE PackagePushRequestId = '{request_id}' AND Status !='Succeeded'"
    subscriber_query = "SELECT OrgKey, OrgName, OrgType, OrgStatus, InstanceName FROM PackageSubscriber WHERE OrgKey IN ({org_ids})"
    gack = re.compile(r"(?P<gack_id>[\d-]+) \((?P<stacktrace_id>[\d-]+)\)")
    headers = [
        "OrganizationId",
        "OrgName",
        "OrgType",
        "OrgStatus",
        "InstanceName",
        "ErrorSeverity",
        "ErrorTitle",
        "ErrorType",
        "ErrorMessage",
        "Gack Id",
        "Stacktrace Id",
    ]

    def _init_options(self, kwargs):
        super(ReportPushFailures, self)._init_options(kwargs)
        self.options["result_file"] = self.options.get("result_file", "push_fails.csv")
        self.options["ignore_errors"] = process_list_arg(
            self.options.get("ignore_errors", "")
        )

    def _run_task(self):
        # Get errors
        formatted_query = self.job_query.format(**self.options)
        self.logger.debug("Running query for job errors: " + formatted_query)
        result = self.sf.query_all(formatted_query)
        job_records = result["records"]
        self.logger.debug(
            "Query is complete: {done}. Found {n} results.".format(
                done=result["done"], n=result["totalSize"]
            )
        )
        if not result["totalSize"]:
            self.logger.info("No errors found.")
            return

        # Sort by error title
        for record in job_records:
            errors = (record.pop("PackagePushErrors", None) or {}).get("records") or [
                {"ErrorTitle": "", "ErrorMessage": ""}
            ]
            error = errors[0]
            m = self.gack.search(error["ErrorMessage"])
            error["GackId"] = m.group("gack_id") if m else ""
            error["StacktraceId"] = m.group("stacktrace_id") if m else ""
            record["Error"] = error
        job_records.sort(
            key=lambda job: (job["Error"]["StacktraceId"], job["Error"]["ErrorTitle"])
        )

        # Get subscriber org info
        self.logger.debug("Running query for subscriber orgs: " + self.subscriber_query)
        org_map = {}
        chunk_size = 100
        for i in range(0, len(job_records), 100):
            org_ids = [
                job["SubscriberOrganizationKey"]
                for job in job_records[i : i + chunk_size]
            ]
            formatted_query = self.subscriber_query.format(
                org_ids=",".join("'{}'".format(org_id) for org_id in org_ids)
            )
            result = self.sf.query_all(formatted_query)
            org_map.update({org["OrgKey"]: org for org in result["records"]})
        self.logger.debug(
            "Query is complete: {done}. Found {n} results.".format(
                done=result["done"], n=len(org_map)
            )
        )

        ignore_errors = self.options["ignore_errors"]
        file_name = self.options["result_file"]
        with open(file_name, "w", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(self.headers)
            for result in job_records:
                error = result["Error"]
                if (
                    error.get("ErrorTitle") in ignore_errors
                    or error.get("ErrorType") in ignore_errors
                ):
                    continue  # pragma: no cover (skipped by compiler's optimizer)
                org = org_map.get(result["SubscriberOrganizationKey"]) or {}
                w.writerow(
                    [
                        result["SubscriberOrganizationKey"],
                        org.get("OrgName", ""),
                        org.get("OrgType", ""),
                        org.get("OrgStatus", ""),
                        org.get("InstanceName", ""),
                        error.get("ErrorSeverity", ""),
                        error.get("ErrorTitle", ""),
                        error.get("ErrorType", ""),
                        error.get("ErrorMessage", ""),
                        error["GackId"],
                        error["StacktraceId"],
                    ]
                )

        self.logger.debug("Written out to {file_name}.".format(file_name=file_name))
        return file_name
