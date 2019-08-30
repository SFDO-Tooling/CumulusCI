from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class PublishCommunity(BaseSalesforceApiTask):
    api_version = "46.0"
    task_docs = """
    Publishes a Salesforce Community via the Connect API.
    """
    task_options = {
        "communityid": {
            "description": "The id of the community to publish.",
            "required": True,
        }
    }

    def _init_options(self, kwargs):
        super(PublishCommunity, self)._init_options(kwargs)
        self.options["timeout"] = int(self.options.get("timeout", 120))

    def _run_task(self):
        self.logger.info(
            'Publishing community "{}"'.format(self.options["communityid"])
        )

        community = self.sf.restful(
            "connect/communities/{}".format(self.options["communityid"])
        )

        self.logger.info(
            "Sending request to publish Community {}".format(community["name"])
        )
        response = self.sf.restful(
            "connect/communities/{}/publish".format(self.options["communityid"]),
            method="POST",
        )

        self.logger.info(response["message"])
