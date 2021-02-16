from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class GetPermissionSetAssignments(BaseSalesforceApiTask):
    def _run_task(self):
        query = f"SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId = '{self.org_config.user_id}'"
        self.return_values = [
            result["PermissionSet"]["Name"]
            for result in self.sf.query_all(query)["records"]
        ]
        permsets = "\n".join(self.return_values)
        self.logger.info(f"Found permission sets assigned:\n{permsets}")
