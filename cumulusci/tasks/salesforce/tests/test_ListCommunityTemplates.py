import responses
import unittest
from cumulusci.tasks.salesforce import ListCommunityTemplates
from .util import create_task


task_options = {}


class test_ListCommunityTemplates(unittest.TestCase):
    @responses.activate
    def test_lists_community_templates(self):
        cc_task = create_task(ListCommunityTemplates, task_options)
        community_url = "{}/services/data/v46.0/connect/communities/templates".format(
            cc_task.org_config.instance_url
        )

        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={
                "templates": [
                    {"publisher": "Salesforce", "templateName": "Build Your Own"},
                    {"publisher": "Salesforce", "templateName": "Koa"},
                    {"publisher": "Salesforce", "templateName": "Help Center"},
                    {"publisher": "Salesforce", "templateName": "Kokua"},
                    {
                        "publisher": "Salesforce",
                        "templateName": "Customer Account Portal",
                    },
                    {"publisher": "Salesforce", "templateName": "Aloha"},
                    {"publisher": "Salesforce", "templateName": "Customer Service"},
                    {"publisher": "Salesforce", "templateName": "Partner Central"},
                    {"publisher": "Salesforce", "templateName": "Customer Service"},
                    {"publisher": "Salesforce", "templateName": "Login Template"},
                    {
                        "publisher": "Salesforce",
                        "templateName": "Salesforce Tabs + Visualforce",
                    },
                ],
                "total": "11",
            },
        )

        cc_task()

        self.assertEqual(1, len(responses.calls))
        self.assertEqual(community_url, responses.calls[0].request.url)
