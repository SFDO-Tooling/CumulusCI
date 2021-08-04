from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class CheckSObjectsAvailable(BaseSalesforceApiTask):
    task_docs = """As a MetaDeploy preflight check, validates that an sObject is present in the schema.

    The task can be used as a preflight check thus::

        3:
            task: insert_sobject_records
            checks:
                - when: "'ContentNote' not in tasks.check_sobjects_available()"
                  action: error
                  message: "Enhanced Notes are not turned on."
    """
    api_version = "48.0"

    def _run_task(self):
        self.return_values = {entry["name"] for entry in self.sf.describe()["sobjects"]}

        self.logger.info(
            "Completed sObjects preflight check with result {}".format(
                self.return_values
            )
        )


class CheckSObjectPerms(BaseSalesforceApiTask):
    task_docs = """As a MetaDeploy preflight check, validates that an sObject's permissions are in the expected state.

    For example, specify::

        check_sobject_permissions:
            options:
                Account:
                    createable: True
                    updateable: False
                Contact:
                    createable: False

    to validate that the Account object is createable but not updateable, and the Contact object is not createable.
    The output is True if all sObjects and permissions are present and matching the specification.

    Given the above configuration, the task can be used as a preflight check in a MetaDeploy plan::

        3:
            task: insert_sobject_records
            checks:
                - when: "not tasks.check_sobject_permissions()"
                  action: error
                  message: "sObject permissions are not configured correctly."
    """

    task_options = {
        "permissions": {
            "description": "The object permissions to check. Each key should be an sObject API name, whose value is a map of describe keys, "
            "such as `queryable` and `createable`, to their desired values (True or False). The output is True if all sObjects and permissions "
            "are present and matching the specification. See the task documentation for examples.",
            "required": True,
        }
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        if type(self.options.get("permissions")) is not dict:
            raise TaskOptionsError(
                "Each sObject should contain a map of permissions to desired values"
            )

        self.permissions = {}
        for sobject, perms in self.options["permissions"].items():
            self.permissions[sobject] = {
                perm: process_bool_arg(value) for perm, value in perms.items()
            }

    def _run_task(self):
        describe = {s["name"]: s for s in self.sf.describe()["sobjects"]}

        success = True

        for sobject, perms in self.permissions.items():
            if sobject not in describe:
                success = False
                self.logger.info(f"sObject {sobject} is not present in the describe.")
            else:
                for perm in perms:
                    if perm not in describe[sobject]:
                        success = False
                        self.logger.info(
                            f"Permission {perm} is not present for sObject {sobject}."
                        )
                    else:
                        if describe[sobject][perm] is not perms[perm]:
                            success = False
                            self.logger.info(
                                f"Permission {perm} for sObject {sobject} is {describe[sobject][perm]}, not {perms[perm]}."
                            )

        self.return_values = success
        self.logger.info(f"Completing preflight check with result {self.return_values}")


class CheckSObjectOWDs(BaseSalesforceApiTask):
    task_docs = """As a MetaDeploy preflight check, validates that an sObject's Org-Wide Defaults are in the expected state.

    For example, specify::

        check_org_wide_defaults:
            options:
                org_wide_defaults:
                    - api_name: Account
                      internal_sharing_model: Private
                      external_sharing_model: Private
                    - api_name: Contact
                      internal_sharing_model: Private

    to validate that the Account object has Private internal and external OWDs, and Contact a Private internal model.
    The output is True if all sObjects and permissions are present and matching the specification.

    Given the above configuration, the task can be used as a preflight check in a MetaDeploy plan::

        3:
            task: insert_sobject_records
            checks:
                - when: "not tasks.check_org_wide_defaults()"
                  action: error
                  message: "Org-Wide Defaults are not configured correctly."
    """
    task_options = {
        "org_wide_defaults": {
            "description": "The Organization-Wide Defaults to check, "
            "organized as a list with each element containing the keys api_name, "
            "internal_sharing_model, and external_sharing_model. NOTE: you must have "
            "External Sharing Model turned on in Sharing Settings to use the latter feature. "
            "Checking External Sharing Model when it is turned off will fail the preflight.",
            "required": True,
        }
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        if "org_wide_defaults" not in self.options:
            raise TaskOptionsError("org_wide_defaults is a required option")

        if not all("api_name" in entry for entry in self.options["org_wide_defaults"]):
            raise TaskOptionsError("api_name must be included in each entry")

        if not all(
            "internal_sharing_model" in entry or "external_sharing_model" in entry
            for entry in self.options["org_wide_defaults"]
        ):
            raise TaskOptionsError("Each entry must include a sharing model to check.")

        self.owds = {
            entry["api_name"]: (
                entry.get("internal_sharing_model"),
                entry.get("external_sharing_model"),
            )
            for entry in self.options["org_wide_defaults"]
        }

    def _check_owds(self, sobject, result):
        internal = (
            result["InternalSharingModel"] == self.owds[sobject][0]
            if self.owds[sobject][0]
            else True
        )
        external = (
            result["ExternalSharingModel"] == self.owds[sobject][1]
            if self.owds[sobject][1]
            else True
        )
        return internal and external

    def _run_task(self):
        try:
            ext = (
                ", ExternalSharingModel"
                if any(owd[1] is not None for owd in self.owds.values())
                else ""
            )
            object_list = ", ".join(f"'{obj}'" for obj in self.owds.keys())
            results = self.sf.query(
                f"SELECT QualifiedApiName, InternalSharingModel{ext} "
                "FROM EntityDefinition "
                f"WHERE QualifiedApiName IN ({object_list})"
            )["records"]
            self.return_values = all(
                self._check_owds(rec["QualifiedApiName"], rec) for rec in results
            )
        except (IndexError, KeyError, SalesforceMalformedRequest):
            self.return_values = False

        self.logger.info(
            f"Completed Organization-Wide Default preflight with result: {self.return_values}"
        )
