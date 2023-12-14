from unittest.mock import Mock

from cumulusci.tasks.preflight.checks import RetrievePreflightChecks
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
from cumulusci.tasks.salesforce import DescribeMetadataTypes
from cumulusci.tasks.salesforce.tests.util import create_task


class TestRetrievePreflightChecks:
    def test_preflight_checks(self):
        task = create_task(
            RetrievePreflightChecks,
            {
                "object_org_wide_defaults": [
                    {"api_name": "Account", "internal_sharing_model": "Private"},
                    {"api_name": "Contact", "internal_sharing_model": "ReadWrite"},
                ],
                "setting_checks": [
                    {
                        "settings_type": "ChatterSettings",
                        "settings_field": "settings_field",
                        "value": True,
                    },
                    {
                        "settings_type": "ChatterSettings",
                        "settings_field": "Foo",
                        "value": "True",
                    },
                ],
                "object_permissions": {
                    "Account": {"createable": True, "updateable": False},
                    "Contact": {"createable": False},
                },
            },
        )

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

        task._call_class = Mock()
        task()

        for cls in classes:
            task._call_class.assert_any_call(cls, {})

        task._call_class.assert_any_call(
            CheckSettingsValue,
            {
                "settings_type": "ChatterSettings",
                "settings_field": "Foo",
                "value": "True",
                "treat_missing_as_failure": False,
            },
        )
        task._call_class.assert_any_call(
            CheckSettingsValue,
            {
                "settings_type": "ChatterSettings",
                "settings_field": "settings_field",
                "value": True,
                "treat_missing_as_failure": False,
            },
        )
        task._call_class.assert_any_call(
            CheckSObjectOWDs,
            {
                "org_wide_defaults": [
                    {"api_name": "Account", "internal_sharing_model": "Private"},
                    {"api_name": "Contact", "internal_sharing_model": "ReadWrite"},
                ]
            },
        )
        task._call_class.assert_any_call(
            CheckSObjectPerms,
            {
                "permissions": {
                    "Account": {"createable": True, "updateable": False},
                    "Contact": {"createable": False},
                }
            },
        )
