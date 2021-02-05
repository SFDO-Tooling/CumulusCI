from cumulusci.tasks.salesforce import BaseSalesforceApiTask

class GetHasRecordTypesForSobject(BaseSalesforceApiTask):
    task_options = {
        "sobject": {
            "description": "The sObject for which we want check if any recordtypes exist",
            "required": True,
        }
    }

    def _run_task(self):
        sobject = self.options["sobject"]
        results = self.tooling.query(
            f"Select  Name FROM RecordType WHERE SobjectType = '{sobject}'"
        )["records"]
        self.return_values = bool(results)
        self.logger.info(
            f"Found existing recordtype for {sobject}: {self.return_values}"
        )
        if self.return_values:
            self.logger.info(f"Found record types for Sobjects:\n{results}")
