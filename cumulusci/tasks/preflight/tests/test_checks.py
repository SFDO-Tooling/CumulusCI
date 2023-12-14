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
                        "value": True,
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

        for cls in classes:
            cls._run_task = Mock()

        CheckSObjectOWDs._run_task = Mock()
        CheckSettingsValue._run_task = Mock()
        CheckSObjectPerms._run_task = Mock()

        task()
        for cls in classes:
            cls._run_task.assert_called_once()

        CheckSObjectOWDs._run_task.assert_called_once()
        CheckSettingsValue._run_task.assert_called_once()
        CheckSObjectPerms._run_task.assert_called_once()
