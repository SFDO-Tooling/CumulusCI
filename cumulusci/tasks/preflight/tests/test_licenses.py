from unittest.mock import Mock

from cumulusci.tasks.preflight.licenses import (
    GetAssignableLicenses,
    GetAssignablePermissionSets,
    GetAvailableLicenses,
    GetAvailablePermissionSetLicenses,
    GetAvailablePermissionSets,
    GetPermissionLicenseSetAssignments,
)
from cumulusci.tasks.salesforce.tests.util import create_task


class TestLicensePreflights:
    def test_license_preflight(self):
        task = create_task(GetAvailableLicenses, {})
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 2,
            "records": [
                {
                    "Id": "L1",
                    "LicenseDefinitionKey": "TEST1",
                    "TotalLicenses": 100,
                    "UsedLicenses": 90,
                },
                {
                    "Id": "L2",
                    "LicenseDefinitionKey": "TEST2",
                    "TotalLicenses": 100,
                    "UsedLicenses": 100,
                },
            ],
        }

        task()
        task._init_api.return_value.query.assert_called_once_with(
            "SELECT Id, LicenseDefinitionKey, TotalLicenses, UsedLicenses FROM UserLicense WHERE Status = 'Active'"
        )

        assert task.return_values == ["TEST1", "TEST2"]

    def test_assignable_license_preflight(self):
        task = create_task(GetAssignableLicenses, {})
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 2,
            "records": [
                {
                    "Id": "L1",
                    "LicenseDefinitionKey": "TEST1",
                    "TotalLicenses": 100,
                    "UsedLicenses": 90,
                },
                {
                    "Id": "L2",
                    "LicenseDefinitionKey": "TEST2",
                    "TotalLicenses": 100,
                    "UsedLicenses": 100,
                },
            ],
        }

        task()
        task._init_api.return_value.query.assert_called_once_with(
            "SELECT Id, LicenseDefinitionKey, TotalLicenses, UsedLicenses FROM UserLicense WHERE Status = 'Active'"
        )
        # Only TEST1 assignable licenses
        assert task.return_values == ["TEST1"]

    def test_psl_preflight(self):
        task = create_task(GetAvailablePermissionSetLicenses, {})
        task._init_api = Mock()

        task._init_api.return_value.query.return_value = {
            "totalSize": 2,
            "records": [
                {"PermissionSetLicenseKey": "TEST1"},
                {"PermissionSetLicenseKey": "TEST2"},
            ],
        }
        task()

        task._init_api.return_value.query.assert_called_once_with(
            "SELECT PermissionSetLicenseKey FROM PermissionSetLicense WHERE Status = 'Active'"
        )
        assert task.return_values == ["TEST1", "TEST2"]

    def test_assigned_permsetlicense_preflight(self):
        task = create_task(GetPermissionLicenseSetAssignments, {})
        task._init_api = Mock()
        task._init_api.return_value.query_all.return_value = {
            "totalSize": 2,
            "done": True,
            "records": [
                {
                    "PermissionSetLicense": {
                        "MasterLabel": "Document Checklist",
                        "DeveloperName": "DocumentChecklist",
                    },
                },
                {
                    "PermissionSetLicense": {
                        "MasterLabel": "Einstein Analytics Plus Admin",
                        "DeveloperName": "EinsteinAnalyticsPlusAdmin",
                    },
                },
            ],
        }
        task()

        task._init_api.return_value.query_all.assert_called_once_with(
            "SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign WHERE AssigneeId = 'USER_ID'"
        )
        assert task.return_values == [
            "DocumentChecklist",
            "EinsteinAnalyticsPlusAdmin",
        ]

    def test_permsets_preflight(self):
        task = create_task(GetAvailablePermissionSets, {})
        task._init_api = Mock()

        task._init_api.return_value.query_all.return_value = {
            "totalSize": 2,
            "records": [
                {"Name": "TEST1"},
                {"Name": "TEST2"},
            ],
        }
        task()

        task._init_api.return_value.query_all.assert_called_once_with(
            "SELECT Name FROM PermissionSet"
        )
        assert task.return_values == ["TEST1", "TEST2"]

    def test_assignable_permsets_preflight(self):
        task = create_task(GetAssignablePermissionSets, {})
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 2,
            "records": [
                {
                    "Id": "L1",
                    "LicenseDefinitionKey": "TEST1",
                    "TotalLicenses": 100,
                    "UsedLicenses": 90,
                },
                {
                    "Id": "L2",
                    "LicenseDefinitionKey": "TEST2",
                    "TotalLicenses": 100,
                    "UsedLicenses": 100,
                },
            ],
        }
        task._init_api.return_value.query_all.return_value = {
            "totalSize": 3,
            "records": [
                {"LicenseId": "L1", "Name": "TEST1"},
                {"LicenseId": "L2", "Name": "TEST2"},
                {"LicenseId": None, "Name": "TEST3"},
            ],
        }
        task()

        task._init_api.return_value.query.assert_called_once_with(
            "SELECT Id, LicenseDefinitionKey, TotalLicenses, UsedLicenses FROM UserLicense WHERE Status = 'Active'"
        )
        task._init_api.return_value.query_all.assert_called_once_with(
            "SELECT LicenseId, Name FROM PermissionSet"
        )
        assert task.return_values == ["TEST1", "TEST3"]
