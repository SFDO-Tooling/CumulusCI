from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class ActivateProcessBuilderProcesses(BaseSalesforceApiTask):
    """
    Create a Salesforce Activation Process Builder which takes in a list as options and
    runs flows only on those listed DeveloperName's.
    """

    def _run_task(self):
        self.logger.info(self.options.get("developer-names"))
        self.logger.info("Querying flow definitions...")
        res = self.tooling.query(
            "SELECT Id,ActiveVersion.VersionNumber,LatestVersion.VersionNumber,DeveloperName FROM FlowDefinition"
        )
        # print(vars(res))
        for listed_flow in res["records"]:
            if listed_flow["DeveloperName"] in self.options.get("developer-names"):
                self.logger.info(f'Processing: {listed_flow["DeveloperName"]}')
                path = "tooling/sobjects/FlowDefinition/{0}".format(listed_flow["Id"])
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
                self.logger.info(
                    f'Skipping DeveloperName: {listed_flow["DeveloperName"]}'
                )
