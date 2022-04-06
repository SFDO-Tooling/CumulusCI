import responses

from cumulusci.tasks.salesforce.create_permission_sets import CreatePermissionSet
from cumulusci.tests.util import CURRENT_SF_API_VERSION

from .util import create_task


class TestCreatePermissionSet:
    @responses.activate
    def test_create_permset(self):
        task = create_task(
            CreatePermissionSet,
            {
                "api_name": "PermSet",
                "label": "Permission Set",
                "user_permissions": [
                    "PermissionsBulkApiHardDelete",
                    "PermissionsCreateAuditFields",
                ],
            },
        )

        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/sobjects/PermissionSet/",
            status=200,
            json={"id": "0PS3F000000fCNPWA2", "success": True, "errors": []},
        )
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/sobjects/PermissionSetAssignment/",
            status=200,
            json={"id": "0Pa000000000001", "success": True, "errors": []},
        )

        task()

        assert len(responses.calls) == 2
        assert "PermissionsBulkApiHardDelete" in responses.calls[0].request.body
        assert "PermissionsCreateAuditFields" in responses.calls[0].request.body
