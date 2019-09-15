from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class ListCommunityTemplates(BaseSalesforceApiTask):
    api_version = "46.0"
    task_docs = """
    Lists Salesforce Community templates available for the current org via the Connect API.
    """
    task_options = {}

    def _init_options(self, kwargs):
        super(ListCommunityTemplates, self)._init_options(kwargs)

    def _run_task(self):
        community_template_list = self.sf.restful("connect/communities/templates")[
            "templates"
        ]

        community_template_names = {
            t["templateName"]: t for t in community_template_list
        }

        self.logger.info(
            "Community Templates available to the current org:%s",
            "\r\n".join(community_template_names),
        )
