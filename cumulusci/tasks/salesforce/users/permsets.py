from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.utils import process_list_arg


class AssignPermissionSets(BaseSalesforceApiTask):
    task_docs = """
Assigns Permission Sets whose Names are in ``api_names`` to either the default org user or the user whose Alias is ``user_alias``. This task skips assigning Permission Sets that are already assigned.
    """

    task_options = {
        "api_names": {
            "description": "API Names of desired Permission Sets, separated by commas.",
            "required": True,
        },
        "user_alias": {
            "description": "Alias of target user (if not the current running user, the default)."
        },
    }

    permission_name = "PermissionSet"
    permission_name_field = "Name"
    permission_label = "Permission Set"
    assignment_name = "PermissionSetAssignment"
    assignment_lookup = "PermissionSetId"
    assignment_child_relationship = "PermissionSetAssignments"

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.options["api_names"] = process_list_arg(self.options["api_names"])

    def _run_task(self):
        # Determine existing assignments
        if "user_alias" not in self.options:
            query = (
                f"SELECT Id,(SELECT {self.assignment_lookup} FROM {self.assignment_child_relationship}) "
                "FROM User "
                f"WHERE Username = '{self.org_config.username}'"
            )
        else:
            query = (
                f"SELECT Id,(SELECT {self.assignment_lookup} FROM {self.assignment_child_relationship}) "
                "FROM User "
                f"""WHERE Alias = '{self.options["user_alias"]}'"""
            )

        result = self.sf.query(query)
        if result["totalSize"] != 1:
            raise CumulusCIException(
                "A single User was not found matching the specified alias."
            )
        user = result["records"][0]

        assigned_perms = {}
        # PermissionSetLicenseAssignments actually returns None if there are no assignments instead of an empty list of records.  Wow.
        if user[self.assignment_child_relationship]:
            assigned_perms = {
                r[self.assignment_lookup]
                for r in user[self.assignment_child_relationship]["records"]
            }

        # Find Ids for requested Perms
        api_names = "', '".join(self.options["api_names"])
        perms = self.sf.query(
            f"SELECT Id,{self.permission_name_field} FROM {self.permission_name} WHERE {self.permission_name_field} IN ('{api_names}')"
        )
        perms = {p[self.permission_name_field]: p["Id"] for p in perms["records"]}

        # Raise for missing perms
        for api_name in self.options["api_names"]:
            if api_name not in perms:
                raise CumulusCIException(
                    f"{self.permission_label} {api_name} was not found."
                )

        # Assign all not already assigned
        for api_name in self.options["api_names"]:
            if perms[api_name] not in assigned_perms:
                self.logger.info(f'Assigning {self.permission_label} "{api_name}".')
                assignment = {
                    "AssigneeId": user["Id"],
                }
                assignment[self.assignment_lookup] = perms[api_name]
                # Create the new assignment.
                getattr(self.sf, self.assignment_name).create(assignment)
            else:
                self.logger.warning(
                    f'{self.permission_label} "{api_name}" is already assigned.'
                )


class AssignPermissionSetLicenses(AssignPermissionSets):
    task_docs = """
Assigns Permission Set Licenses whose Developer Names are in ``api_names`` to either the default org user or the user whose Alias is ``user_alias``. This task skips assigning Permission Set Licenses that are already assigned.

Permission Set Licenses are usually associated with a Permission Set, and assigning the Permission Set usually assigns the associated Permission Set License automatically.  However, in non-namespaced developer scratch orgs, assigning the associated Permission Set may not automatically assign the Permission Set License, and this task will ensure the Permission Set Licenses are assigned.
    """

    task_options = {
        "api_names": {
            "description": "API Developer Names of desired Permission Set Licenses, separated by commas.",
            "required": True,
        },
        "user_alias": {
            "description": "Alias of target user (if not the current running user, the default)."
        },
    }

    permission_name = "PermissionSetLicense"
    permission_name_field = "DeveloperName"
    permission_label = "Permission Set License"
    assignment_name = "PermissionSetLicenseAssign"
    assignment_lookup = "PermissionSetLicenseId"
    assignment_child_relationship = "PermissionSetLicenseAssignments"


class AssignPermissionSetGroups(AssignPermissionSets):
    task_docs = """
Assigns Permission Set Groups whose Developer Names are in ``api_names`` to either the default org user or the user whose Alias is ``user_alias``. This task skips assigning Permission Set Groups that are already assigned.
    """

    task_options = {
        "api_names": {
            "description": "API Developer Names of desired Permission Set Groups, separated by commas.",
            "required": True,
        },
        "user_alias": {
            "description": "Alias of target user (if not the current running user, the default)."
        },
    }

    permission_name = "PermissionSetGroup"
    permission_name_field = "DeveloperName"
    permission_label = "Permission Set Group"
    assignment_name = "PermissionSetAssignment"
    assignment_lookup = "PermissionSetGroupId"
    assignment_child_relationship = "PermissionSetAssignments"
