from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.utils import process_list_arg


class AssignPermissionSets(BaseSalesforceApiTask):
    task_options = {
        "api_names": {
            "description": "API names of desired Permission Sets, separated by commas.",
            "required": True,
        },
        "user_alias": {
            "description": "Alias of target user (if not the current running user, the default)."
        }
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.options["api_names"] = process_list_arg(self.options["api_names"])

    def _run_task(self):
        # Determine existing assignments
        if "user_alias" not in self.options:
            query = f"""SELECT Id,
                            (SELECT PermissionSetId
                             FROM PermissionSetAssignments)
                        FROM User
                        WHERE Username = '{self.org_config.username}'"""
        else:
            query = f"""SELECT Id,
                            (SELECT PermissionSetId
                             FROM PermissionSetAssignments)
                        FROM User
                        WHERE Alias = '{self.options["user_alias"]}'"""

        result = self.sf.query(query)
        if result["totalSize"] != 1:
            raise CumulusCIException("A single User was not found matching the specified alias.")
        user = result["records"][0]

        assigned_permsets = {
            r["PermissionSetId"] for r in user["PermissionSetAssignments"]["records"]
        }

        # Find Ids for requested Perm Sets
        api_names = "', '".join(self.options["api_names"])
        permsets = self.sf.query(
            f"SELECT Id, Name FROM PermissionSet WHERE Name IN ('{api_names}')"
        )
        permsets = {p["Name"]: p["Id"] for p in permsets["records"]}

        # Raise for missing permsets
        for api_name in self.options["api_names"]:
            if api_name not in permsets:
                raise CumulusCIException(f"Permission Set {api_name} was not found.")

        # Assign all not already assigned
        for api_name in self.options["api_names"]:
            if permsets[api_name] not in assigned_permsets:
                self.logger.info(f"Assigning permission set {api_name}.")
                self.sf.PermissionSetAssignment.create(
                    {
                        "AssigneeId": user["Id"],
                        "PermissionSetId": permsets[api_name],
                    }
                )
            else:
                self.logger.info(f"Permission set {api_name} is already assigned.")

