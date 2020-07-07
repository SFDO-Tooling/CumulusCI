import requests
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class IsCommunitiesEnabled(BaseSalesforceApiTask):
    api_version = "48.0"

    def _run_task(self):
        s = requests.Session()
        s.get(self.org_config.start_url).raise_for_status()
        r = s.get(
            "{}/sites/servlet.SitePrerequisiteServlet".format(
                self.org_config.instance_url
            )
        )
        if r.status_code != 200:
            self.return_values = False
        else:
            self.return_values = True

        self.logger.info(
            "Completed Communities preflight check with result {}".format(
                self.return_values
            )
        )
