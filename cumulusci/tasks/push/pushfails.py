""" simple task(s) for reporting on push upgrade jobs.

this doesn't use the nearby push_api module, and was just a quick ccistyle
get the job done kinda moment.
"""

import re
import csv
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class PushFailTask(BaseSalesforceApiTask):
    """ Produce a report of the failed and otherwise anomalous push jobs from
    a specified push request id, and write it out to a results CSV.  """

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
    gack = re.compile(r"error number: ([\d-]+) \(([\d-]+)\)")
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
                error = result["PackagePushErrors"]["records"][0]
                m = self.gack.search(error["ErrorMessage"])
                w.writerow(
                    [
                        result["SubscriberOrganizationKey"],
                        error["ErrorSeverity"],
                        error["ErrorTitle"],
                        error["ErrorType"],
                        error["ErrorMessage"],
                        m.groups()[0] if m else "",
                        m.groups()[1] if m else "",
                    ]
                )

        self.logger.debug("Written out to {file_name}.".format(file_name=file_name))
        return records
