""" simple task(s) for reporting on push upgrade jobs.

this doesn't use the nearby push_api module, and was just a quick ccistyle
get the job done kinda moment.
"""

import re
import csv
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class ReportPushFailures(BaseSalesforceApiTask):
    """ Produce a report of the failed and otherwise anomalous push jobs.

    Takes a push request id and writes results to a CSV file.  """

    task_doc = __doc__
    task_options = {
        "request_id": {
            "description": "PackagePushRequest ID for the request you need to report on.",
            "required": True,
        },
        "result_file": {"description": "Where to write results"},
    }
    api_version = "43.0"
    query = "SELECT ID, SubscriberOrganizationKey, (SELECT ErrorDetails, ErrorMessage, ErrorSeverity, ErrorTitle, ErrorType FROM PackagePushErrors) FROM PackagePushJob WHERE PackagePushRequestId = '{request_id}' AND Status !='Succeeded'"
    gack = re.compile(
        r"error number: (?P<gack_id>[\d-]+) \((?P<stacktrace_id>[\d-]+)\)"
    )
    headers = [
        "OrganizationId",
        "ErrorSeverity",
        "ErrorTitle",
        "ErrorType",
        "ErrorMessage",
        "Gack Id",
        "Stacktrace Id",
    ]

    def _run_task(self):
        formatted_query = self.query.format(**self.options)
        self.logger.debug("Running query: " + formatted_query)

        result = self.sf.query(formatted_query)
        records = result["records"]
        self.logger.debug(
            "Query is complete: {done}. Found {n} results.".format(
                done=result["done"], n=result["totalSize"]
            )
        )

        file_name = self.options.get("result_file", "push_fails.csv")
        with open(file_name, "wb") as f:
            w = csv.writer(f)
            w.writerow(self.headers)
            for result in records:
                if not result.get("PackagePushErrors", {}).get("records", None):
                    w.writerow(
                        [
                            result["SubscriberOrganizationKey"],
                            None,
                            None,
                            None,
                            None,
                            None,
                        ]
                    )
                    continue
                error = result["PackagePushErrors"]["records"][0]
                m = self.gack.search(error["ErrorMessage"])
                w.writerow(
                    [
                        result["SubscriberOrganizationKey"],
                        error["ErrorSeverity"],
                        error["ErrorTitle"],
                        error["ErrorType"],
                        error["ErrorMessage"],
                        m.group("gack_id") if m else "",
                        m.group("stacktrace_id") if m else "",
                    ]
                )

        self.logger.debug("Written out to {file_name}.".format(file_name=file_name))
        return file_name
