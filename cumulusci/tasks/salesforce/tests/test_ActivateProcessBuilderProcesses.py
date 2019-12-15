# from unittest import mock
import unittest
import json
from cumulusci.tasks.salesforce.ActivateFlowProcesses import ActivateFlowProcesses

# from cumulusci.core.exceptions import SalesforceException
# from simple_salesforce.exceptions import SalesforceMalformedRequest
from .util import create_task
import responses


task_options = {
    "developer_names": {
        "description": (
            "Activates Flows identified by a given list of Developer Names"
        ),
        "developer_names": [
            "Auto_Populate_Date_And_Name_On_Program_Engagement",
            "ape",
        ],
        "required": True,
    },
}
# task_options = {
#     "name": "Test Community",
#     "description": "Community Details",
#     "template": "VF Template",
#     "url_path_prefix": "test",
# }
# task_options_no_url_path_prefix = {
#     "name": "Test Community",
#     "description": "Community Details",
#     "template": "VF Template",
# }


class TestActivateFlowProcesses(unittest.TestCase):
    @responses.activate
    def test_activate_flow_processes(self):
        # project_config = BaseProjectConfig(
        #     BaseGlobalConfig(),
        #     {"project": {"package": {"name": "TestPackage", "api_version": "43.0"}}},
        # )
        cc_task = create_task(ActivateFlowProcesses, task_options)
        # print()
        servlet_url = "{}/sites/servlet.SitePrerequisiteServlet".format(
            cc_task.org_config.instance_url
        )

        activate_url = "{}/tooling/sobjects/FlowDefinition/3001F0000009GFwQAM".format(
            cc_task.org_config.instance_url
        )
        responses.add(
            method="GET",
            url="https://test.salesforce.com/services/data/v47.0/tooling/query/?q=SELECT+Id%2C+ActiveVersion.VersionNumber%2C+LatestVersion.VersionNumber%2C+DeveloperName+FROM+FlowDefinition+WHERE+DeveloperName+IN+%28%27Auto_Populate_Date_And_Name_On_Program_Engagement%27%2C%27ape%27%29",
            body=json.dumps(
                {
                    "records": [
                        {
                            "Id": "3001F0000009GFwQAM",
                            "DeveloperName": "Auto_Populate_Date_And_Name_On_Program_Engagement",
                            "LatestVersion": {"VersionNumber": "47.0"},
                        }
                    ]
                }
            ),
            status=200,
        )
        responses.add(
            method="GET",
            url="http://api/job/3/batch/4/result",
            body=json.dumps(
                {
                    "records": [
                        {
                            "Id": "3001F0000009GFwQAM",
                            "DeveloperName": "Auto_Populate_Date_And_Name_On_Program_Engagement",
                            "LatestVersion": {"VersionNumber": "47.0"},
                        }
                    ]
                }
            ),
            status=200,
        )
        responses.add(
            method=responses.GET, url=cc_task.org_config.start_url, status=200
        )
        responses.add(method=responses.GET, url=servlet_url, status=200)
        responses.add(method=responses.PATCH, url=activate_url, status=204)

        # responses.add(method=responses.POST, url=community_url, status=200, json={})
        # responses.add(
        #     method=responses.GET,
        #     url=community_url,
        #     status=200,
        #     json={"communities": [{"name": "Test Community", "id": "000000000000000"}]},
        # )

        cc_task()

        self.assertEqual(4, len(responses.calls))
        self.assertEqual(cc_task.org_config.start_url, responses.calls[0].request.url)
        self.assertEqual(servlet_url, responses.calls[1].request.url)
        self.assertEqual(activate_url, responses.calls[2].request.url)
        self.assertEqual(activate_url, responses.calls[3].request.url)
        # self.assertEqual(
        #     json.dumps(
        #         {
        #             "name": "Test Community",
        #             "description": "Community Details",
        #             "templateName": "VF Template",
        #             "urlPathPrefix": "test",
        #         }
        #     ),
        #     responses.calls[2].request.body,
        # )
