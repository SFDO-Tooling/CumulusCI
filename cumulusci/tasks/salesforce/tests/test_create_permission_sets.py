import responses

from cumulusci.tasks.salesforce.create_permission_sets import CreatePermissionSet

from .util import create_task


class TestCreatePermissionSet:
    @responses.activate
    def test_create_permset(self, sf_url):
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
        base_url = sf_url(task.org_config)

        responses.add(
            method="POST",
            url=f"{base_url}/sobjects/PermissionSet/",
            status=200,
            json={"id": "0PS3F000000fCNPWA2", "success": True, "errors": []},
        )
        responses.add(
            method="POST",
            url=f"{base_url}/sobjects/PermissionSetAssignment/",
            status=200,
            json={"id": "0Pa000000000001", "success": True, "errors": []},
        )

        task()

        assert len(responses.calls) == 2
        assert "PermissionsBulkApiHardDelete" in responses.calls[0].request.body
        assert "PermissionsCreateAuditFields" in responses.calls[0].request.body
