import json

import pytest
import responses

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.activate_flow import ActivateFlow

from .util import create_task


class TestActivateFlow:
    @responses.activate
    def test_activate_some_flow_processes(self):
        cc_task = create_task(
            ActivateFlow,
            {
                "developer_names": [
                    "Auto_Populate_Date_And_Name_On_Program_Engagement",
                    "ape",
                ]
            },
        )
        record_id = "3001F0000009GFwQAM"
        activate_url = (
            "{}/services/data/v43.0/tooling/sobjects/FlowDefinition/{}".format(
                cc_task.org_config.instance_url, record_id
            )
        )
        responses.add(
            method="GET",
            url="https://test.salesforce.com/services/data/v43.0/tooling/query/?q=SELECT+Id%2C+ActiveVersion.VersionNumber%2C+LatestVersion.VersionNumber%2C+DeveloperName+FROM+FlowDefinition+WHERE+DeveloperName+IN+%28%27Auto_Populate_Date_And_Name_On_Program_Engagement%27%2C%27ape%27%29",
            body=json.dumps(
                {
                    "records": [
                        {
                            "Id": record_id,
                            "DeveloperName": "Auto_Populate_Date_And_Name_On_Program_Engagement",
                            "LatestVersion": {"VersionNumber": 1},
                        }
                    ]
                }
            ),
            status=200,
        )
        data = {"Metadata": {"activeVersionNumber": 1}}
        responses.add(method=responses.PATCH, url=activate_url, status=204, json=data)

        cc_task()
        assert 2 == len(responses.calls)

    @responses.activate
    def test_activate_all_flow_processes(self):
        cc_task = create_task(
            ActivateFlow,
            {
                "developer_names": [
                    "Auto_Populate_Date_And_Name_On_Program_Engagement",
                    "ape",
                ]
            },
        )
        record_id = "3001F0000009GFwQAM"
        record_id2 = "3001F0000009GFwQAW"
        activate_url = (
            "{}/services/data/v43.0/tooling/sobjects/FlowDefinition/{}".format(
                cc_task.org_config.instance_url, record_id
            )
        )
        activate_url2 = (
            "{}/services/data/v43.0/tooling/sobjects/FlowDefinition/{}".format(
                cc_task.org_config.instance_url, record_id2
            )
        )
        responses.add(
            method="GET",
            url="https://test.salesforce.com/services/data/v43.0/tooling/query/?q=SELECT+Id%2C+ActiveVersion.VersionNumber%2C+LatestVersion.VersionNumber%2C+DeveloperName+FROM+FlowDefinition+WHERE+DeveloperName+IN+%28%27Auto_Populate_Date_And_Name_On_Program_Engagement%27%2C%27ape%27%29",
            body=json.dumps(
                {
                    "records": [
                        {
                            "Id": record_id,
                            "DeveloperName": "Auto_Populate_Date_And_Name_On_Program_Engagement",
                            "LatestVersion": {"VersionNumber": 1},
                        },
                        {
                            "Id": record_id2,
                            "DeveloperName": "ape",
                            "LatestVersion": {"VersionNumber": 1},
                        },
                    ]
                }
            ),
            status=200,
        )
        data = {"Metadata": {"activeVersionNumber": 1}}
        responses.add(method=responses.PATCH, url=activate_url, status=204, json=data)
        responses.add(method=responses.PATCH, url=activate_url2, status=204, json=data)
        cc_task()
        assert 3 == len(responses.calls)

    @responses.activate
    def test_activate_no_flow_processes(self):
        with pytest.raises(TaskOptionsError):
            cc_task = create_task(ActivateFlow, {"developer_names": []})
            cc_task()
