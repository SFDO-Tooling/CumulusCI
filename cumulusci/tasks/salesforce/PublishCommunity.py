from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import SalesforceException


class PublishCommunity(BaseSalesforceApiTask):
    api_version = "46.0"
    task_docs = """
    Publishes a Salesforce Community via the Connect API.
    """
    task_options = {
        "name": {
            "description": "The name of the Community to publish.",
            "required": True,
        },
        "communityid": {
            "description": "The id of the Community to publish.",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super(PublishCommunity, self)._init_options(kwargs)

    def _run_task(self):
        community_id = self.options.get("communityid", None)
        community_name = self.options["name"]

        if community_id is None:
            self.logger.info(
                'Finding id for Community "{}"'.format(self.options["name"])
            )
            community_list = self.sf.restful("connect/communities")["communities"]
            communities = {c["name"]: c for c in community_list}

            if self.options["name"] in communities:
                community_id = communities[self.options["name"]]["id"]
            else:
                raise SalesforceException(
                    'Unable to find a Community named "{}"'.format(community_id)
                )
        else:
            self.logger.info('Checking name for community "{}"'.format(community_id))
            community = self.sf.restful("connect/communities/{}".format(community_id))
            if community_name != community["name"]:
                raise SalesforceException(
                    'The Community name for {} is "{}" and does not match "{}", the name you provided'.format(
                        community_id, community["name"], community_name
                    )
                )

        self.logger.info(
            'Sending request to publish Community "{}"({})'.format(
                community_name, community_id
            )
        )
        response = self.sf.restful(
            "connect/communities/{}/publish".format(community_id), method="POST"
        )

        self.logger.info(response["message"])
