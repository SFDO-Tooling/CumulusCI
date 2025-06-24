import json

import pytest
import responses

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.activate_flow import ActivateFlow
from cumulusci.tests.util import CURRENT_SF_API_VERSION

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
                ],
                "status": True,
            },
        )
        record_id = "3001F0000009GFwQAM"
        activate_url = f"{cc_task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/FlowDefinition/{record_id}"
        responses.add(
            method="GET",
            url=f"https://test.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id%2C+ActiveVersion.VersionNumber%2C+LatestVersion.VersionNumber%2C+DeveloperName+FROM+FlowDefinition+WHERE+DeveloperName+IN+%28%27Auto_Populate_Date_And_Name_On_Program_Engagement%27%2C%27ape%27%29",
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
        responses.add(method=responses.PATCH, url=activate_url, status=204)

        cc_task()
        assert 2 == len(responses.calls)

    @responses.activate
    def test_deactivate_some_flow_processes(self):
        cc_task = create_task(
            ActivateFlow,
            {
                "developer_names": [
                    "Auto_Populate_Date_And_Name_On_Program_Engagement",
                    "ape",
                ],
                "status": False,
            },
        )
        record_id = "3001F0000009GFwQAM"
        activate_url = f"{cc_task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/FlowDefinition/{record_id}"
        responses.add(
            method="GET",
            url=f"https://test.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id%2C+ActiveVersion.VersionNumber%2C+LatestVersion.VersionNumber%2C+DeveloperName+FROM+FlowDefinition+WHERE+DeveloperName+IN+%28%27Auto_Populate_Date_And_Name_On_Program_Engagement%27%2C%27ape%27%29",
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

        responses.add(method=responses.PATCH, url=activate_url, status=204)

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
                ],
                "status": True,
            },
        )
        record_id = "3001F0000009GFwQAM"
        record_id2 = "3001F0000009GFwQAW"
        activate_url = f"{cc_task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/FlowDefinition/{record_id}"
        activate_url2 = f"{cc_task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/FlowDefinition/{record_id2}"
        responses.add(
            method="GET",
            url=f"https://test.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id%2C+ActiveVersion.VersionNumber%2C+LatestVersion.VersionNumber%2C+DeveloperName+FROM+FlowDefinition+WHERE+DeveloperName+IN+%28%27Auto_Populate_Date_And_Name_On_Program_Engagement%27%2C%27ape%27%29",
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

        responses.add(method=responses.PATCH, url=activate_url, status=204)
        responses.add(method=responses.PATCH, url=activate_url2, status=204)
        cc_task()
        assert 3 == len(responses.calls)

    @responses.activate
    def test_activate_no_flow_processes(self):
        with pytest.raises(TaskOptionsError):
            cc_task = create_task(ActivateFlow, {"developer_names": []})
            cc_task()
