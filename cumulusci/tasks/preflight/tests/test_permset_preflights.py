from unittest.mock import Mock

from cumulusci.tasks.preflight.permsets import GetPermissionSetAssignments
from cumulusci.tasks.salesforce.tests.util import create_task


class TestPermsetPreflights:
    def test_assigned_permset_preflight(self):
        task = create_task(GetPermissionSetAssignments, {})
        task._init_api = Mock()
        task._init_api.return_value.query_all.return_value = {
            "totalSize": 2,
            "done": True,
            "records": [
                {
                    "PermissionSet": {
                        "Label": "Document Checklist",
                        "Name": "DocumentChecklist",
                    },
                },
                {
                    "PermissionSet": {
                        "Label": "Einstein Analytics Plus Admin",
                        "Name": "EinsteinAnalyticsPlusAdmin",
                    },
                },
            ],
        }
        task()

        task._init_api.return_value.query_all.assert_called_once_with(
            "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId = 'USER_ID'"
        )
        assert task.return_values == [
            "DocumentChecklist",
            "EinsteinAnalyticsPlusAdmin",
        ]
