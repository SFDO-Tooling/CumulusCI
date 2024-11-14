from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class GetPermissionSetAssignments(BaseSalesforceApiTask):
    def _run_task(self):
        query = f"SELECT PermissionSet.Name,PermissionSetGroupId FROM PermissionSetAssignment WHERE AssigneeId = '{self.org_config.user_id}'"

        self.return_values = []
        for result in self.sf.query_all(query)["records"]:
            if result["PermissionSet"]["Name"] not in self.return_values:
                self.return_values.append(result["PermissionSet"]["Name"])
            if result["PermissionSetGroupId"] is not None:
                psg_query = f"SELECT PermissionSet.Name from PermissionSetGroupComponent where PermissionSetGroupId = '{result['PermissionSetGroupId']}'"
                for psg_result in self.sf.query_all(psg_query)["records"]:
                    if (
                        psg_result["PermissionSet"]
                        and psg_result["PermissionSet"]["Name"]
                        not in self.return_values
                    ):
                        self.return_values.append(psg_result["PermissionSet"]["Name"])

        permsets_str = "\n".join(self.return_values)
        self.logger.info(f"Found permission sets assigned:\n{permsets_str}")
