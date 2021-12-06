import json

from cumulusci.cli.ui import CliTable
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


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
            "description": "Target user aliases, separated by commas. Defaults to the current running user."
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
        self.options["user_alias"] = process_list_arg(
            self.options.get("user_alias") or []
        )

    def _run_task(self):
        users = self._query_existing_assignments()
        users_assigned_perms = {
            user["Id"]: self._get_assigned_perms(user) for user in users
        }
        perms_by_id = self._get_perm_ids()

        records_to_insert = []
        for user_id, assigned_perms in users_assigned_perms.items():
            records_to_insert.extend(
                self._get_assignments(user_id, assigned_perms, perms_by_id)
            )

        self._insert_assignments(records_to_insert)

    def _query_existing_assignments(self):
        if not self.options["user_alias"]:
            query = (
                f"SELECT Id,(SELECT {self.assignment_lookup} FROM {self.assignment_child_relationship}) "
                "FROM User "
                f"WHERE Username = '{self.org_config.username}'"
            )
        else:
            aliases = "','".join(self.options["user_alias"])
            query = (
                f"SELECT Id,(SELECT {self.assignment_lookup} FROM {self.assignment_child_relationship}) "
                "FROM User "
                f"""WHERE Alias IN ('{aliases}')"""
            )

        result = self.sf.query(query)
        if result["totalSize"] == 0:
            raise CumulusCIException(
                "No Users were found matching the specified aliases."
            )
        return result["records"]

    def _get_assigned_perms(self, user):
        assigned_perms = {}
        # PermissionSetLicenseAssignments actually returns None if there are no assignments instead of an empty list of records.  Wow.
        if user[self.assignment_child_relationship]:
            assigned_perms = {
                r[self.assignment_lookup]
                for r in user[self.assignment_child_relationship]["records"]
            }
        return assigned_perms

    def _get_perm_ids(self):
        api_names = "', '".join(self.options["api_names"])
        perms = self.sf.query(
            f"SELECT Id,{self.permission_name_field} FROM {self.permission_name} WHERE {self.permission_name_field} IN ('{api_names}')"
        )
        perms_by_ids = {
            p["Id"]: p[self.permission_name_field] for p in perms["records"]
        }

        missing_perms = [
            api_name
            for api_name in self.options["api_names"]
            if api_name not in perms_by_ids.values()
        ]
        if missing_perms:
            raise CumulusCIException(
                f"The following {self.permission_label}s were not found: {', '.join(missing_perms)}."
            )
        return perms_by_ids

    def _get_assignments(self, user_id, assigned_perms, perms_by_id):
        assignments = []
        for perm, perm_name in perms_by_id.items():
            if perm not in assigned_perms:
                self.logger.info(
                    f'Assigning {self.permission_label} "{perm_name}" to {user_id}.'
                )
                assignment = {
                    "attributes": {"type": self.assignment_name},
                    "AssigneeId": user_id,
                    self.assignment_lookup: perm,
                }
                assignments.append(assignment)
            else:
                self.logger.warning(
                    f'{self.permission_label} "{perm_name}" is already assigned to {user_id}.'
                )
        return assignments

    def _insert_assignments(self, records_to_insert):
        result_list = []
        for i in range(0, len(records_to_insert), 200):
            request_body = json.dumps(
                {"allOrNone": False, "records": records_to_insert[i : i + 200]}
            )
            result = self.sf.restful(
                "composite/sobjects", method="POST", data=request_body
            )
            result_list.extend(result)
        self._process_composite_results(result_list)

    def _process_composite_results(self, api_results):
        results_table_data = [["Success", "ID", "Message"]]
        for result in api_results:
            result_row = [result["success"], result.get("id", "-")]
            if not result["success"] and result["errors"]:
                result_row.append(result["errors"][0]["message"])
            else:
                result_row.append("-")
            results_table_data.append(result_row)

        table = CliTable(
            results_table_data,
            title="Results",
        )
        table.echo()

        if not all([result["success"] for result in api_results]):
            raise CumulusCIException(
                f"Not all {self.assignment_child_relationship} were saved."
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
