import responses
import pytest

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce.users.permsets import AssignPermissionSets
from cumulusci.tasks.salesforce.tests.util import create_task


class TestCreatePermissionSet:
    @responses.activate
    def test_create_permset(self):
        task = create_task(
            AssignPermissionSets,
            {
                "api_names": "PermSet1,PermSet2",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%0A++++++++++++++++++++++++++++%28SELECT+PermissionSetId%0A+++++++++++++++++++++++++++++FROM+PermissionSetAssignments%29%0A++++++++++++++++++++++++FROM+User%0A++++++++++++++++++++++++WHERE+Username+%3D+%27test-cci%40example.com%27",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "005000000000000",
                        "PermissionSetAssignments": {
                            "done": True,
                            "totalSize": 1,
                            "records": [{"PermissionSetId": "0PS000000000000"}],
                        },
                    }
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C+Name+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet1%27%2C+%27PermSet2%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0PS000000000000",
                        "Name": "PermSet1",
                    },
                    {
                        "Id": "0PS000000000001",
                        "Name": "PermSet2",
                    },
                ],
            },
        )
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v50.0/sobjects/PermissionSetAssignment/",
            status=200,
            json={"id": "0Pa000000000001", "success": True, "errors": []},
        )

        task()

        assert len(responses.calls) == 3
        assert "0PS000000000001" in responses.calls[2].request.body

    @responses.activate
    def test_create_permset__alias(self):
        task = create_task(
            AssignPermissionSets,
            {
                "api_names": "PermSet1,PermSet2",
                "user_alias": "test",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%0A++++++++++++++++++++++++++++%28SELECT+PermissionSetId%0A+++++++++++++++++++++++++++++FROM+PermissionSetAssignments%29%0A++++++++++++++++++++++++FROM+User%0A++++++++++++++++++++++++WHERE+Alias+%3D+%27test%27",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "005000000000000",
                        "PermissionSetAssignments": {
                            "done": True,
                            "totalSize": 1,
                            "records": [{"PermissionSetId": "0PS000000000000"}],
                        },
                    }
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C+Name+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet1%27%2C+%27PermSet2%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0PS000000000000",
                        "Name": "PermSet1",
                    },
                    {
                        "Id": "0PS000000000001",
                        "Name": "PermSet2",
                    },
                ],
            },
        )
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v50.0/sobjects/PermissionSetAssignment/",
            status=200,
            json={"id": "0Pa000000000001", "success": True, "errors": []},
        )

        task()

        assert len(responses.calls) == 3
        assert "0PS000000000001" in responses.calls[2].request.body

    @responses.activate
    def test_create_permset__alias_raises(self):
        task = create_task(
            AssignPermissionSets,
            {
                "api_names": "PermSet1,PermSet2",
                "user_alias": "test",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%0A++++++++++++++++++++++++++++%28SELECT+PermissionSetId%0A+++++++++++++++++++++++++++++FROM+PermissionSetAssignments%29%0A++++++++++++++++++++++++FROM+User%0A++++++++++++++++++++++++WHERE+Alias+%3D+%27test%27",
            status=200,
            json={
                "done": True,
                "totalSize": 0,
                "records": [],
            },
        )
        with pytest.raises(CumulusCIException):
            task()


    @responses.activate
    def test_create_permset_raises(self):
        task = create_task(
            AssignPermissionSets,
            {
                "api_names": "PermSet1,PermSet2,PermSet3",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%0A++++++++++++++++++++++++++++%28SELECT+PermissionSetId%0A+++++++++++++++++++++++++++++FROM+PermissionSetAssignments%29%0A++++++++++++++++++++++++FROM+User%0A++++++++++++++++++++++++WHERE+Username+%3D+%27test-cci%40example.com%27",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "005000000000000",
                        "PermissionSetAssignments": {
                            "done": True,
                            "totalSize": 1,
                            "records": [{"PermissionSetId": "0PS000000000000"}],
                        },
                    }
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C+Name+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet1%27%2C+%27PermSet2%27%2C+%27PermSet3%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0PS000000000000",
                        "Name": "PermSet1",
                    },
                    {
                        "Id": "0PS000000000001",
                        "Name": "PermSet2",
                    },
                ],
            },
        )

        with pytest.raises(CumulusCIException):
            task()
