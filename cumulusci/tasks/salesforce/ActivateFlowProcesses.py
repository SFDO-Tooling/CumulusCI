from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.utils import process_list_arg
import click


class ActivateFlowProcesses(BaseSalesforceApiTask):
    """
    Activate the Flows with the supplied Developer Names
    """

    task_options = {
        "developer_names": {
            "description": "List of DeveloperNames to query in SOQL",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super(ActivateFlowProcesses, self)._init_options(kwargs)
        self.options["developer_names"] = process_list_arg(
            # self.task_config.options["developer_names"]
            self.options.get("developer_names")
        )

    api_version = "43.0"

    def _run_task(self):
        if self.options["developer_names"]:
            self.logger.info(
                f"Activating the following Flows: {self.options['developer_names']}"
            )
            self.logger.info("Querying flow definitions...")
            result = self.tooling.query(
                "SELECT Id, ActiveVersion.VersionNumber, LatestVersion.VersionNumber, DeveloperName FROM FlowDefinition WHERE DeveloperName IN ({0})".format(
                    ",".join([f"'{n}'" for n in self.options["developer_names"]])
                )
            )
            for listed_flow in result["records"]:
                self.logger.info(f'Processing: {listed_flow["DeveloperName"]}')
                path = f"tooling/sobjects/FlowDefinition/{listed_flow['Id']}"
                urlpath = self.sf.base_url + path
                data = {
                    "Metadata": {
                        "activeVersionNumber": listed_flow["LatestVersion"][
                            "VersionNumber"
                        ]
                    }
                }
                response = self.tooling._call_salesforce("PATCH", urlpath, json=data)
                self.logger.info(response)
        else:
            click.echo(
                "Error you are missing developer_names definition in your task cumulusci.yml file. Please pass in developer_names for your task configuration or use -o to developer_names as a commandline arg"
            )
