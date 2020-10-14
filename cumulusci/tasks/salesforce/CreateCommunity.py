import json
from datetime import datetime

from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.exceptions import CumulusCIException, SalesforceException
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class CreateCommunity(BaseSalesforceApiTask):
    api_version = "48.0"
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
            "required": False,
        },
        "retries": {
            "description": "Number of times to retry community creation request"
        },
        "timeout": {
            "description": "Time to wait, in seconds, for the community to be created"
        },
        "skip_existing": {
            "description": "If True, an existing community with the "
            "same name will not raise an exception."
        },
    }

    def _init_options(self, kwargs):
        super(CreateCommunity, self)._init_options(kwargs)
        self.options["retries"] = int(self.options.get("retries", 6))
        self.options["timeout"] = int(self.options.get("timeout", 300))
        self.options["skip_existing"] = process_bool_arg(
            self.options.get("skip_existing", False)
        )

    def _run_task(self):
        community = self._get_community()
        if community is not None:
            error_msg = f'A community named "{self.options["name"]}" already exists.'
            if self.options["skip_existing"]:
                self.logger.info(error_msg)
                return
            raise CumulusCIException(error_msg)

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
                community = self._get_community()
                self.poll_complete = True
                self.logger.info("Community {} created".format(community["id"]))
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

        community = self._get_community()
        if community is not None:
            self.poll_complete = True
            self.logger.info("Community {} created".format(community["id"]))

    def _get_community(self):
        community_list = self.sf.restful("connect/communities")["communities"]
        communities = {c["name"]: c for c in community_list}
        return communities.get(self.options["name"])
