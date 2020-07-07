from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class IsCommunitiesEnabled(BaseSalesforceApiTask):
    api_version = "48.0"

    def _run_task(self):
        self.return_values = "Network" in {
            entry["name"] for entry in self.sf.describe()["sobjects"]
        }

        self.logger.info(
            "Completed Communities preflight check with result {}".format(
                self.return_values
            )
        )
