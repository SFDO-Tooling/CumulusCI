from rst2ansi import rst2ansi

from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class ListCommunities(BaseSalesforceApiTask):
    api_version = "46.0"
    task_docs = """
    Lists Communities for the current org via the Connect API.
    """
    task_options = {}

    def _run_task(self):
        communities = self.sf.restful("connect/communities")["communities"]

        nameString = "\n==========================================\n"

        communities_output = ["The current Communities in the org are:\n"]
        for community in communities:
            communities_output.append("\n{}{}".format(community["name"], nameString))
            communities_output.append("* **Id:** {}\n".format(community["id"]))
            communities_output.append("* **Status:** {}\n".format(community["status"]))
            communities_output.append(
                "* **Site Url:** `<{}>`_\n".format(community["siteUrl"])
            )
            communities_output.append(
                "* **Url Path Prefix:** {}\n".format(
                    community.get("urlPathPrefix") or ""
                )
            )
            communities_output.append(
                "* **Template:** {}\n".format(community["templateName"])
            )
            communities_output.append(
                "* **Description:** {}\n".format(community["description"])
            )

        communities_output2 = "\n".join(communities_output).encode("utf-8")
        self.logger.info(rst2ansi(communities_output2))
        self.return_values = [community["name"] for community in communities]
