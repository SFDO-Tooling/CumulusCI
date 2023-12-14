from cumulusci.core.config import TaskConfig
from cumulusci.tasks.preflight.licenses import (
    GetAvailableLicenses,
    GetAvailablePermissionSetLicenses,
    GetAvailablePermissionSets,
    GetPermissionLicenseSetAssignments,
)
from cumulusci.tasks.preflight.packages import GetInstalledPackages
from cumulusci.tasks.preflight.permsets import GetPermissionSetAssignments
from cumulusci.tasks.preflight.recordtypes import CheckSObjectRecordTypes
from cumulusci.tasks.preflight.settings import CheckMyDomainActive, CheckSettingsValue
from cumulusci.tasks.preflight.sobjects import (
    CheckSObjectOWDs,
    CheckSObjectPerms,
    CheckSObjectsAvailable,
)
from cumulusci.tasks.salesforce import BaseSalesforceApiTask, DescribeMetadataTypes


class RetrievePreflightChecks(BaseSalesforceApiTask):
    task_options = {
        "object_permissions": {
            "description": "The object permissions to check. Each key should be an sObject API name, whose value is a map of describe keys, "
            "such as `queryable` and `createable`, to their desired values (True or False). The output is True if all sObjects and permissions "
            "are present and matching the specification. See the task documentation for examples."
        },
        "treat_missing_setting_as_failure": {
            "description": "If True, treat a missing Settings entity as a preflight failure, instead of raising an exception. Defaults to False.",
        },
        "setting_checks": {
            "description": "To check whether the setting entity has the given field or not "
        },
        "object_org_wide_defaults": {
            "description": "The Organization-Wide Defaults to check, "
            "organized as a list with each element containing the keys api_name, "
            "internal_sharing_model, and external_sharing_model. NOTE: you must have "
            "External Sharing Model turned on in Sharing Settings to use the latter feature. "
            "Checking External Sharing Model when it is turned off will fail the preflight.",
        },
    }

    def _init_task(self):
        super()._init_task()

    def _run_task(self):

        classes = [
            CheckMyDomainActive,
            GetAvailableLicenses,
            GetAvailablePermissionSetLicenses,
            GetPermissionLicenseSetAssignments,
            GetAvailablePermissionSets,
            GetInstalledPackages,
            GetPermissionSetAssignments,
            CheckSObjectRecordTypes,
            CheckSObjectsAvailable,
            DescribeMetadataTypes,
        ]

        self.return_values = {
            cls.__name__: cls(
                org_config=self.org_config,
                project_config=self.project_config,
                task_config=self.task_config,
            )()
            for cls in classes
        }

        if "object_permissions" in self.options:
            task_config = TaskConfig(
                {"options": {"permissions": self.options["object_permissions"]}}
            )
            self.return_values["CheckSObjectPerms"] = CheckSObjectPerms(
                org_config=self.org_config,
                project_config=self.project_config,
                task_config=task_config,
            )()
        if "object_org_wide_defaults" in self.options:
            task_config = TaskConfig(
                {
                    "options": {
                        "org_wide_defaults": self.options["object_org_wide_defaults"]
                    }
                }
            )

            self.return_values["CheckSObjectOWDs"] = CheckSObjectOWDs(
                org_config=self.org_config,
                project_config=self.project_config,
                task_config=task_config,
            )()

        if "treat_missing_setting_as_failure" not in self.options:
            self.options["treat_missing_setting_as_failure"] = False

        if "setting_checks" in self.options:
            self.return_values["CheckSettingsValue"] = True
            self.setting_checks = {
                (entry["settings_type"], entry["settings_field"], entry["value"])
                for entry in self.options["setting_checks"]
            }

            for type, field, value in self.setting_checks:
                task_config = task_config = TaskConfig(
                    {
                        "options": {
                            "settings_type": type,
                            "settings_field": field,
                            "value": value,
                            "treat_missing_as_failure": self.options[
                                "treat_missing_setting_as_failure"
                            ],
                        }
                    }
                )
                self.return_values["CheckSettingsValue"] = (
                    self.return_values["CheckSettingsValue"]
                    and CheckSettingsValue(
                        org_config=self.org_config,
                        project_config=self.project_config,
                        task_config=task_config,
                    )()
                )
                if not self.return_values["CheckSettingsValue"]:
                    break
