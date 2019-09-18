import json
import requests
from datetime import datetime
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import SalesforceException


class CreateCommunity(BaseSalesforceApiTask):
    api_version = "46.0"
    task_docs = """
    Create a Salesforce Community via the Connect API.
    Specify the `template` "VF Template" for Visualforce Tabs community,
    or the name for a specific desired template
    """
    task_options = {
        "template": {
            "description": "Name of the template for the community.",
            "required": True,
        },
        "name": {"description": "Name of the community.", "required": True},
        "description": {
            "description": "Description of the community.",
            "required": False,
        },
        "url_path_prefix": {
            "description": "URL prefix for the community.",
            "required": True,
        },
        "timeout": {
            "description": "Time to wait, in seconds, for the community to be created",
            "default": 120,
        },
    }

    def _init_options(self, kwargs):
        super(CreateCommunity, self)._init_options(kwargs)
        self.options["timeout"] = int(self.options.get("timeout", 120))

    def _run_task(self):
        self.logger.info('Creating community "{}"'.format(self.options["name"]))
        payload = {
            "name": self.options["name"],
            "description": self.options.get("description") or "",
            "templateName": self.options["template"],
            "urlPathPrefix": self.options["url_path_prefix"],
        }

        # Before we can create a Community, we have to click through the "New Community"
        # button in the All Communities setup page. (This does some unknown behind-the-scenes setup).
        # Let's simulate that without actually using a browser.
        self.logger.info("Preparing org for Communities")
        s = requests.Session()
        s.get(self.org_config.start_url).raise_for_status()
        r = s.get(
            "{}/sites/servlet.SitePrerequisiteServlet".format(
                self.org_config.instance_url
            )
        )
        if r.status_code != 200:
            raise SalesforceException("Unable to prepare org for Communities")

        self.logger.info("Sending request to create Community")
        self.sf.restful("connect/communities", method="POST", data=json.dumps(payload))

        # Wait for the community to be created
        self.time_start = datetime.now()
        self._poll()

    def _poll_action(self):
        elapsed = datetime.now() - self.time_start
        if elapsed.total_seconds() > self.options["timeout"]:
            raise SalesforceException(
                "Community creation not finished after {timeout} seconds".format(
                    **self.options
                )
            )

        community_list = self.sf.restful("connect/communities")["communities"]
        communities = {c["name"]: c for c in community_list}
        if self.options["name"] in communities:
            self.poll_complete = True
            self.logger.info(
                "Community {} created".format(communities[self.options["name"]]["id"])
            )
