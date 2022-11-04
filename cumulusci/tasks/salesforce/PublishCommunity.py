from cumulusci.core.exceptions import SalesforceException, TaskOptionsError
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class PublishCommunity(BaseSalesforceApiTask):
    api_version = "46.0"
    task_docs = """
    Publish a Salesforce Community via the Connect API. Warning: This does not work with the Community Template 'VF Template' due to an existing bug in the API.
    """
    task_options = {
        "name": {
            "description": "The name of the Community to publish.",
            "required": False,
        },
        "community_id": {
            "description": "The id of the Community to publish.",
            "required": False,
        },
    }

    def _run_task(self):
        community_id = self.options.get("community_id", None)
        community_name = self.options.get("name", None)

        if community_id is None:
            if community_name is None:
                missing_required = ["name", "community_id"]
                raise TaskOptionsError(
                    "{} requires one of options ({}) "
                    "and no values were provided".format(
                        self.__class__.__name__, ", ".join(missing_required)
                    )
                )

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

            self.logger.info(
                'Sending request to publish Community "{}" ({})'.format(
                    community_name, community_id
                )
            )
        else:
            self.logger.info(
                "Sending request to publish Community ({})".format(community_id)
            )

        response = self.sf.restful(
            "connect/communities/{}/publish".format(community_id), method="POST"
        )

        self.logger.info(response["message"])
