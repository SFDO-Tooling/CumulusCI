import responses
import pytest

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce.users.permsets import (
    AssignPermissionSets,
    AssignPermissionSetLicenses,
    AssignPermissionSetGroups,
)
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
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2CName+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet1%27%2C+%27PermSet2%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Alias+%3D+%27test%27",
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
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2CName+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet1%27%2C+%27PermSet2%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Alias+%3D+%27test%27",
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
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2CName+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet1%27%2C+%27PermSet2%27%2C+%27PermSet3%27%29",
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


class TestCreatePermissionSetLicense:
    @responses.activate
    def test_create_permsetlicense(self):
        task = create_task(
            AssignPermissionSetLicenses,
            {
                "api_names": "PermSetLicense1,PermSetLicense2",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetLicenseId+FROM+PermissionSetLicenseAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "005000000000000",
                        "PermissionSetLicenseAssignments": {
                            "done": True,
                            "totalSize": 1,
                            "records": [{"PermissionSetLicenseId": "0PL000000000000"}],
                        },
                    }
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetLicense+WHERE+DeveloperName+IN+%28%27PermSetLicense1%27%2C+%27PermSetLicense2%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0PL000000000000",
                        "DeveloperName": "PermSetLicense1",
                    },
                    {
                        "Id": "0PL000000000001",
                        "DeveloperName": "PermSetLicense2",
                    },
                ],
            },
        )
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v50.0/sobjects/PermissionSetLicenseAssign/",
            status=200,
            json={"id": "0Pa000000000001", "success": True, "errors": []},
        )

        task()

        assert len(responses.calls) == 3
        assert "0PL000000000001" in responses.calls[2].request.body

    @responses.activate
    def test_create_permsetlicense__no_assignments(self):
        task = create_task(
            AssignPermissionSetLicenses,
            {
                "api_names": "PermSetLicense1,PermSetLicense2",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetLicenseId+FROM+PermissionSetLicenseAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "005000000000000",
                        # This seems like a bug: the PermissionSetLicenseAssignments sub-query returns None if no PSLs are already assigned instead of returning an "empty list".
                        "PermissionSetLicenseAssignments": None,
                    }
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetLicense+WHERE+DeveloperName+IN+%28%27PermSetLicense1%27%2C+%27PermSetLicense2%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0PL000000000000",
                        "DeveloperName": "PermSetLicense1",
                    },
                    {
                        "Id": "0PL000000000001",
                        "DeveloperName": "PermSetLicense2",
                    },
                ],
            },
        )
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v50.0/sobjects/PermissionSetLicenseAssign/",
            status=200,
            json={"id": "0Pa000000000000", "success": True, "errors": []},
        )
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v50.0/sobjects/PermissionSetLicenseAssign/",
            status=200,
            json={"id": "0Pa000000000001", "success": True, "errors": []},
        )

        task()

        assert len(responses.calls) == 4
        assert "0PL000000000000" in responses.calls[2].request.body
        assert "0PL000000000001" in responses.calls[3].request.body

    @responses.activate
    def test_create_permsetlicense__alias(self):
        task = create_task(
            AssignPermissionSetLicenses,
            {
                "api_names": "PermSetLicense1,PermSetLicense2",
                "user_alias": "test",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetLicenseId+FROM+PermissionSetLicenseAssignments%29+FROM+User+WHERE+Alias+%3D+%27test%27",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "005000000000000",
                        "PermissionSetLicenseAssignments": {
                            "done": True,
                            "totalSize": 1,
                            "records": [{"PermissionSetLicenseId": "0PL000000000000"}],
                        },
                    }
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetLicense+WHERE+DeveloperName+IN+%28%27PermSetLicense1%27%2C+%27PermSetLicense2%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0PL000000000000",
                        "DeveloperName": "PermSetLicense1",
                    },
                    {
                        "Id": "0PL000000000001",
                        "DeveloperName": "PermSetLicense2",
                    },
                ],
            },
        )
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v50.0/sobjects/PermissionSetLicenseAssign/",
            status=200,
            json={"id": "0Pa000000000001", "success": True, "errors": []},
        )

        task()

        assert len(responses.calls) == 3
        assert "0PL000000000001" in responses.calls[2].request.body

    @responses.activate
    def test_create_permsetlicense__alias_raises(self):
        task = create_task(
            AssignPermissionSetLicenses,
            {
                "api_names": "PermSetLicense1,PermSetLicense2",
                "user_alias": "test",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetLicenseId+FROM+PermissionSetLicenseAssignments%29+FROM+User+WHERE+Alias+%3D+%27test%27",
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
    def test_create_permsetlicense_raises(self):
        task = create_task(
            AssignPermissionSetLicenses,
            {
                "api_names": "PermSetLicense1,PermSetLicense2,PermSetLicense3",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetLicenseId+FROM+PermissionSetLicenseAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "005000000000000",
                        "PermissionSetLicenseAssignments": {
                            "done": True,
                            "totalSize": 1,
                            "records": [{"PermissionSetLicenseId": "0PL000000000000"}],
                        },
                    }
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetLicense+WHERE+DeveloperName+IN+%28%27PermSetLicense1%27%2C+%27PermSetLicense2%27%2C+%27PermSetLicense3%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0PL000000000000",
                        "DeveloperName": "PermSetLicense1",
                    },
                    {
                        "Id": "0PL000000000001",
                        "DeveloperName": "PermSetLicense2",
                    },
                ],
            },
        )

        with pytest.raises(CumulusCIException):
            task()


class TestCreatePermissionSetGroup:
    @responses.activate
    def test_create_permsetgroup(self):
        task = create_task(
            AssignPermissionSetGroups,
            {
                "api_names": "PermSetGroup1,PermSetGroup2",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetGroupId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
                            "records": [{"PermissionSetGroupId": "0PG000000000000"}],
                        },
                    }
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetGroup+WHERE+DeveloperName+IN+%28%27PermSetGroup1%27%2C+%27PermSetGroup2%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0PG000000000000",
                        "DeveloperName": "PermSetGroup1",
                    },
                    {
                        "Id": "0PG000000000001",
                        "DeveloperName": "PermSetGroup2",
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
        assert "0PG000000000001" in responses.calls[2].request.body

    @responses.activate
    def test_create_permsetgroup__alias(self):
        task = create_task(
            AssignPermissionSetGroups,
            {
                "api_names": "PermSetGroup1,PermSetGroup2",
                "user_alias": "test",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetGroupId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Alias+%3D+%27test%27",
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
                            "records": [{"PermissionSetGroupId": "0PG000000000000"}],
                        },
                    }
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetGroup+WHERE+DeveloperName+IN+%28%27PermSetGroup1%27%2C+%27PermSetGroup2%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0PG000000000000",
                        "DeveloperName": "PermSetGroup1",
                    },
                    {
                        "Id": "0PG000000000001",
                        "DeveloperName": "PermSetGroup2",
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
        assert "0PG000000000001" in responses.calls[2].request.body

    @responses.activate
    def test_create_permsetgroup__alias_raises(self):
        task = create_task(
            AssignPermissionSetGroups,
            {
                "api_names": "PermSetGroup1,PermSetGroup2",
                "user_alias": "test",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetGroupId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Alias+%3D+%27test%27",
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
    def test_create_permsetgroup_raises(self):
        task = create_task(
            AssignPermissionSetGroups,
            {
                "api_names": "PermSetGroup1,PermSetGroup2,PermSetGroup3",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2C%28SELECT+PermissionSetGroupId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
                            "records": [{"PermissionSetGroupId": "0PG000000000000"}],
                        },
                    }
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v50.0/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetGroup+WHERE+DeveloperName+IN+%28%27PermSetGroup1%27%2C+%27PermSetGroup2%27%2C+%27PermSetGroup3%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 1,
                "records": [
                    {
                        "Id": "0PG000000000000",
                        "DeveloperName": "PermSetGroup1",
                    },
                    {
                        "Id": "0PG000000000001",
                        "DeveloperName": "PermSetGroup2",
                    },
                ],
            },
        )

        with pytest.raises(CumulusCIException):
            task()
