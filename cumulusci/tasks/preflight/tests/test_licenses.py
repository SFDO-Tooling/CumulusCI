from unittest.mock import Mock

from cumulusci.tasks.preflight.licenses import (
    GetAvailableLicenses,
    GetAvailablePermissionSetLicenses,
    GetAvailablePermissionSets,
)
from cumulusci.tasks.salesforce.tests.util import create_task


class TestLicensePreflights:
    def test_license_preflight(self):
        task = create_task(GetAvailableLicenses, {})
        task._init_api = Mock()
        task._init_api.return_value.query.return_value = {
            "totalSize": 2,
            "records": [
                {"LicenseDefinitionKey": "TEST1"},
                {"LicenseDefinitionKey": "TEST2"},
            ],
        }
        task()

        task._init_api.return_value.query.assert_called_once_with(
            "SELECT LicenseDefinitionKey FROM UserLicense"
        )
        assert task.return_values == ["TEST1", "TEST2"]

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
            "SELECT PermissionSetLicenseKey FROM PermissionSetLicense"
        )
        assert task.return_values == ["TEST1", "TEST2"]

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
