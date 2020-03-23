from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class ListCommunityTemplates(BaseSalesforceApiTask):
    api_version = "46.0"
    task_docs = """
    Lists Salesforce Community templates available for the current org via the Connect API.
    """
    task_options = {}

    def _run_task(self):
        community_template_list = self.sf.restful("connect/communities/templates")[
            "templates"
        ]

        self.logger.info(
            "Community Templates available to the current org:\n%s",
            "\n".join(t["templateName"] for t in community_template_list),
        )
