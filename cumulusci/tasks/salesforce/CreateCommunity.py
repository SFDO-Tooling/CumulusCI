import json
from datetime import datetime

from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import SalesforceException


class CreateCommunity(BaseSalesforceApiTask):
    api_version = "48.0"
    task_docs = """Create a Salesforce Community via the Connect API.

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
            "required": False,
        },
        "retries": {
            "description": "Number of times to retry community creation request"
        },
        "timeout": {
            "description": "Time to wait, in seconds, for the community to be created"
        },
    }

    def _init_options(self, kwargs):
        super(CreateCommunity, self)._init_options(kwargs)
        self.options["retries"] = int(self.options.get("retries", 6))
        self.options["timeout"] = int(self.options.get("timeout", 300))

    def _run_task(self):
        self.logger.info('Creating community "{}"'.format(self.options["name"]))

        tries = 0
        while True:
            tries += 1
            try:
                self._create_community()
            except Exception as e:
                if tries > self.options["retries"]:
                    raise
                else:
                    self.logger.warning(str(e))
                    self.logger.info("Retrying community creation request")
                    self.poll_interval_s = 1
            else:
                break  # pragma: no cover

    def _create_community(self):
        payload = {
            "name": self.options["name"],
            "description": self.options.get("description") or "",
            "templateName": self.options["template"],
            "urlPathPrefix": self.options.get("url_path_prefix") or "",
        }

        self.logger.info("Sending request to create Community")
        try:
            self.sf.restful(
                "connect/communities", method="POST", data=json.dumps(payload)
            )
        except SalesforceMalformedRequest as e:
            if "Error: A Community with this name already exists" in str(e):
                # We can end up here if the previous try timed out
                # but the community finished creating before we tried again.
                self._check_completion()
                return
            else:
                raise

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
        self._check_completion()

    def _check_completion(self):
        community_list = self.sf.restful("connect/communities")["communities"]
        communities = {c["name"]: c for c in community_list}
        if self.options["name"] in communities:
            self.poll_complete = True
            self.logger.info(
                "Community {} created".format(communities[self.options["name"]]["id"])
            )
