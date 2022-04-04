import json
from unittest.mock import patch

import pytest
import responses

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.salesforce.users.permsets import (
    AssignPermissionSetGroups,
    AssignPermissionSetLicenses,
    AssignPermissionSets,
)
from cumulusci.tests.util import CURRENT_SF_API_VERSION


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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CName+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet1%27%2C+%27PermSet2%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 2,
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            status=200,
            json=[{"id": "0Pa000000000001", "success": True, "errors": []}],
            match=[
                responses.json_params_matcher(
                    {
                        "allOrNone": False,
                        "records": [
                            {
                                "attributes": {"type": "PermissionSetAssignment"},
                                "AssigneeId": "005000000000000",
                                "PermissionSetId": "0PS000000000001",
                            }
                        ],
                    }
                ),
            ],
        )

        task()

        assert len(responses.calls) == 3

    @responses.activate
    def test_create_permset__alias(self):
        task = create_task(
            AssignPermissionSets,
            {
                "api_names": "PermSet1,PermSet2",
                "user_alias": "test0,test1",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Alias+IN+%28%27test0%27%2C%27test1%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 2,
                "records": [
                    {
                        "Id": "005000000000000",
                        "PermissionSetAssignments": {
                            "done": True,
                            "totalSize": 1,
                            "records": [{"PermissionSetId": "0PS000000000000"}],
                        },
                    },
                    {
                        "Id": "005000000000001",
                        "PermissionSetAssignments": {
                            "done": True,
                            "totalSize": 1,
                            "records": [{"PermissionSetId": "0PS000000000000"}],
                        },
                    },
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CName+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet1%27%2C+%27PermSet2%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            status=200,
            json=[
                {"id": "0Pa000000000000", "success": True, "errors": []},
                {"id": "0Pa000000000001", "success": True, "errors": []},
            ],
            match=[
                responses.json_params_matcher(
                    {
                        "allOrNone": False,
                        "records": [
                            {
                                "attributes": {"type": "PermissionSetAssignment"},
                                "AssigneeId": "005000000000000",
                                "PermissionSetId": "0PS000000000001",
                            },
                            {
                                "attributes": {"type": "PermissionSetAssignment"},
                                "AssigneeId": "005000000000001",
                                "PermissionSetId": "0PS000000000001",
                            },
                        ],
                    }
                ),
            ],
        )

        task()

        assert len(responses.calls) == 3

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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Alias+IN+%28%27test%27%29",
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
    def test_create_permset__split_requests(self):
        task = create_task(
            AssignPermissionSets,
            {
                "api_names": ",".join(["PermSet" + str(i) for i in range(20)]),
                "user_alias": ",".join(["test" + str(i) for i in range(20)]),
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Alias+IN+%28%27test0%27%2C%27test1%27%2C%27test2%27%2C%27test3%27%2C%27test4%27%2C%27test5%27%2C%27test6%27%2C%27test7%27%2C%27test8%27%2C%27test9%27%2C%27test10%27%2C%27test11%27%2C%27test12%27%2C%27test13%27%2C%27test14%27%2C%27test15%27%2C%27test16%27%2C%27test17%27%2C%27test18%27%2C%27test19%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 20,
                "records": [
                    {
                        "Id": f"00500000000000{str(i)}",
                        "PermissionSetAssignments": None,
                    }
                    for i in range(20)
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CName+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet0%27%2C+%27PermSet1%27%2C+%27PermSet2%27%2C+%27PermSet3%27%2C+%27PermSet4%27%2C+%27PermSet5%27%2C+%27PermSet6%27%2C+%27PermSet7%27%2C+%27PermSet8%27%2C+%27PermSet9%27%2C+%27PermSet10%27%2C+%27PermSet11%27%2C+%27PermSet12%27%2C+%27PermSet13%27%2C+%27PermSet14%27%2C+%27PermSet15%27%2C+%27PermSet16%27%2C+%27PermSet17%27%2C+%27PermSet18%27%2C+%27PermSet19%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 20,
                "records": [
                    {
                        "Id": f"0PS000000000000{str(i)}",
                        "Name": f"PermSet{str(i)}",
                    }
                    for i in range(20)
                ],
            },
        )
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            status=200,
            json=[
                {"id": f"0Pa00000000000{str(i)}", "success": True, "errors": []}
                for i in range(200)
            ],
        )

        task()

        assert len(responses.calls) == 4
        assert len(json.loads(responses.calls[2].request.body)["records"]) == 200
        assert len(json.loads(responses.calls[3].request.body)["records"]) == 200

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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CName+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet1%27%2C+%27PermSet2%27%2C+%27PermSet3%27%29",
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

    @responses.activate
    @patch("cumulusci.tasks.salesforce.users.permsets.CliTable", autospec=True)
    def test_create_permset_partial_success_raises(self, table):
        task = create_task(
            AssignPermissionSets,
            {
                "api_names": "PermSet1,PermSet2",
                "user_alias": "test0,test1",
            },
        )

        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Alias+IN+%28%27test0%27%2C%27test1%27%29",
            status=200,
            json={
                "done": True,
                "totalSize": 2,
                "records": [
                    {
                        "Id": "005000000000000",
                        "PermissionSetAssignments": {
                            "done": True,
                            "totalSize": 1,
                            "records": [{"PermissionSetId": "0PS000000000000"}],
                        },
                    },
                    {
                        "Id": "005000000000001",
                        "PermissionSetAssignments": {
                            "done": True,
                            "totalSize": 1,
                            "records": [{"PermissionSetId": "0PS000000000000"}],
                        },
                    },
                ],
            },
        )
        responses.add(
            method="GET",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CName+FROM+PermissionSet+WHERE+Name+IN+%28%27PermSet1%27%2C+%27PermSet2%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            status=200,
            json=[
                {"id": "0Pa000000000000", "success": True, "errors": []},
                {
                    "success": False,
                    "errors": [
                        {
                            "fields": [],
                            "statusCode": "FOO",
                            "message": "Delphic exception message",
                        }
                    ],
                },
            ],
            match=[
                responses.json_params_matcher(
                    {
                        "allOrNone": False,
                        "records": [
                            {
                                "attributes": {"type": "PermissionSetAssignment"},
                                "AssigneeId": "005000000000000",
                                "PermissionSetId": "0PS000000000001",
                            },
                            {
                                "attributes": {"type": "PermissionSetAssignment"},
                                "AssigneeId": "005000000000001",
                                "PermissionSetId": "0PS000000000001",
                            },
                        ],
                    }
                ),
            ],
        )

        with pytest.raises(CumulusCIException):
            task()

        # Check table output
        expected_table_data = [
            ["Success", "ID", "Message"],
            [True, "0Pa000000000000", "-"],
            [False, "-", "Delphic exception message"],
        ]
        table.assert_called_once()
        assert expected_table_data in table.call_args[0]


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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetLicenseId+FROM+PermissionSetLicenseAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetLicense+WHERE+DeveloperName+IN+%28%27PermSetLicense1%27%2C+%27PermSetLicense2%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            status=200,
            json=[{"id": "0Pa000000000001", "success": True, "errors": []}],
            match=[
                responses.json_params_matcher(
                    {
                        "allOrNone": False,
                        "records": [
                            {
                                "attributes": {"type": "PermissionSetLicenseAssign"},
                                "AssigneeId": "005000000000000",
                                "PermissionSetLicenseId": "0PL000000000001",
                            }
                        ],
                    }
                ),
            ],
        )

        task()

        assert len(responses.calls) == 3

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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetLicenseId+FROM+PermissionSetLicenseAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetLicense+WHERE+DeveloperName+IN+%28%27PermSetLicense1%27%2C+%27PermSetLicense2%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            status=200,
            json=[
                {"id": "0Pa000000000000", "success": True, "errors": []},
                {"id": "0Pa000000000001", "success": True, "errors": []},
            ],
            match=[
                responses.json_params_matcher(
                    {
                        "allOrNone": False,
                        "records": [
                            {
                                "attributes": {"type": "PermissionSetLicenseAssign"},
                                "AssigneeId": "005000000000000",
                                "PermissionSetLicenseId": "0PL000000000000",
                            },
                            {
                                "attributes": {"type": "PermissionSetLicenseAssign"},
                                "AssigneeId": "005000000000000",
                                "PermissionSetLicenseId": "0PL000000000001",
                            },
                        ],
                    }
                ),
            ],
        )
        task()

        assert len(responses.calls) == 3

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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetLicenseId+FROM+PermissionSetLicenseAssignments%29+FROM+User+WHERE+Alias+IN+%28%27test%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetLicense+WHERE+DeveloperName+IN+%28%27PermSetLicense1%27%2C+%27PermSetLicense2%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/sobjects/PermissionSetLicenseAssign/",
            status=200,
            json={"id": "0Pa000000000001", "success": True, "errors": []},
        )

        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            status=200,
            json=[{"id": "0Pa000000000001", "success": True, "errors": []}],
            match=[
                responses.json_params_matcher(
                    {
                        "allOrNone": False,
                        "records": [
                            {
                                "attributes": {"type": "PermissionSetLicenseAssign"},
                                "AssigneeId": "005000000000000",
                                "PermissionSetLicenseId": "0PL000000000001",
                            }
                        ],
                    }
                ),
            ],
        )
        task()

        assert len(responses.calls) == 3

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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetLicenseId+FROM+PermissionSetLicenseAssignments%29+FROM+User+WHERE+Alias+IN+%28%27test%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetLicenseId+FROM+PermissionSetLicenseAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetLicense+WHERE+DeveloperName+IN+%28%27PermSetLicense1%27%2C+%27PermSetLicense2%27%2C+%27PermSetLicense3%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetGroupId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetGroup+WHERE+DeveloperName+IN+%28%27PermSetGroup1%27%2C+%27PermSetGroup2%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            status=200,
            json=[{"id": "0Pa000000000001", "success": True, "errors": []}],
            match=[
                responses.json_params_matcher(
                    {
                        "allOrNone": False,
                        "records": [
                            {
                                "attributes": {"type": "PermissionSetAssignment"},
                                "AssigneeId": "005000000000000",
                                "PermissionSetGroupId": "0PG000000000001",
                            }
                        ],
                    }
                ),
            ],
        )

        task()

        assert len(responses.calls) == 3

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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetGroupId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Alias+IN+%28%27test%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetGroup+WHERE+DeveloperName+IN+%28%27PermSetGroup1%27%2C+%27PermSetGroup2%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite/sobjects",
            status=200,
            json=[{"id": "0Pa000000000001", "success": True, "errors": []}],
            match=[
                responses.json_params_matcher(
                    {
                        "allOrNone": False,
                        "records": [
                            {
                                "attributes": {"type": "PermissionSetAssignment"},
                                "AssigneeId": "005000000000000",
                                "PermissionSetGroupId": "0PG000000000001",
                            }
                        ],
                    }
                ),
            ],
        )

        task()

        assert len(responses.calls) == 3

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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetGroupId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Alias+IN+%28%27test%27%29",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2C%28SELECT+PermissionSetGroupId+FROM+PermissionSetAssignments%29+FROM+User+WHERE+Username+%3D+%27test-cci%40example.com%27",
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
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id%2CDeveloperName+FROM+PermissionSetGroup+WHERE+DeveloperName+IN+%28%27PermSetGroup1%27%2C+%27PermSetGroup2%27%2C+%27PermSetGroup3%27%29",
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
