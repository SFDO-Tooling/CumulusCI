import unittest

import responses
from simple_salesforce.exceptions import SalesforceResourceNotFound

from cumulusci.core.api_version import API_VERSION
from cumulusci.core.exceptions import SalesforceException, TaskOptionsError
from cumulusci.tasks.salesforce import PublishCommunity

from .util import create_task

task_options = {"name": "Test Community"}
task_options_with_id = {"name": "Test Community", "community_id": "000000000000000000"}


class test_PublishCommunity(unittest.TestCase):
    @responses.activate
    def test_publishes_community(self):
        cc_task = create_task(PublishCommunity, task_options)
        communities_url = f"{cc_task.org_config.instance_url}/services/data/v{API_VERSION}/connect/communities"
        community_publish_url = f"{cc_task.org_config.instance_url}/services/data/v{API_VERSION}/connect/communities/{task_options_with_id['community_id']}/publish"

        responses.add(
            method=responses.GET,
            url=communities_url,
            status=200,
            json={
                "communities": [
                    {
                        "allowChatterAccessWithoutLogin": "false",
                        "allowMembersToFlag": "false",
                        "description": "This is a test community",
                        "id": task_options_with_id["community_id"],
                        "invitationsEnabled": "false",
                        "knowledgeableEnabled": "false",
                        "loginUrl": "https://mydomain.force.com/test/s/login",
                        "memberVisibilityEnabled": "true",
                        "name": task_options["name"],
                        "nicknameDisplayEnabled": "false",
                        "privateMessagesEnabled": "false",
                        "reputationEnabled": "false",
                        "sendWelcomeEmail": "true",
                        "siteAsContainerEnabled": "true",
                        "siteUrl": "https://mydomain.force.com/test",
                        "status": "Live",
                        "templateName": "VF Template",
                        "url": f"/services/data/v{API_VERSION}/connect/communities/{task_options_with_id['community_id']}",
                        "urlPathPrefix": "test",
                    }
                ],
                "total": "1",
            },
        )

        responses.add(
            method=responses.POST,
            url=community_publish_url,
            status=200,
            json={
                "id": "{}".format(task_options_with_id["community_id"]),
                "message": "We are publishing your changes now. You will receive an email confirmation when your changes are live.",
                "name": "{}".format(task_options["name"]),
                "url": "https://mydomain.force.com/test",
            },
        )

        cc_task()

        self.assertEqual(2, len(responses.calls))
        self.assertEqual(communities_url, responses.calls[0].request.url)
        self.assertEqual(community_publish_url, responses.calls[1].request.url)

    @responses.activate
    def test_publishes_community_with_id(self):
        cc_task = create_task(PublishCommunity, task_options_with_id)
        community_publish_url = f"{cc_task.org_config.instance_url}/services/data/v{API_VERSION}/connect/communities/{task_options_with_id['community_id']}/publish"

        responses.add(
            method=responses.POST,
            url=community_publish_url,
            status=200,
            json={
                "id": "{}".format(task_options_with_id["community_id"]),
                "message": "We are publishing your changes now. You will receive an email confirmation when your changes are live.",
                "name": "{}".format(task_options_with_id["name"]),
                "url": "https://mydomain.force.com/test",
            },
        )

        cc_task()

        self.assertEqual(1, len(responses.calls))
        self.assertEqual(community_publish_url, responses.calls[0].request.url)

    @responses.activate
    def test_throws_exception_for_bad_name(self):
        cc_task = create_task(PublishCommunity, task_options)
        communities_url = f"{cc_task.org_config.instance_url}/services/data/v{API_VERSION}/connect/communities"

        responses.add(
            method=responses.GET,
            url=communities_url,
            status=200,
            json={
                "communities": [
                    {
                        "allowChatterAccessWithoutLogin": "false",
                        "allowMembersToFlag": "false",
                        "description": "This is a test community",
                        "id": "{}".format(task_options_with_id["community_id"]),
                        "invitationsEnabled": "false",
                        "knowledgeableEnabled": "false",
                        "loginUrl": "https://mydomain.force.com/test/s/login",
                        "memberVisibilityEnabled": "true",
                        "name": "Not {}".format(task_options["name"]),
                        "nicknameDisplayEnabled": "false",
                        "privateMessagesEnabled": "false",
                        "reputationEnabled": "false",
                        "sendWelcomeEmail": "true",
                        "siteAsContainerEnabled": "true",
                        "siteUrl": "https://mydomain.force.com/test",
                        "status": "Live",
                        "templateName": "VF Template",
                        "url": f"/services/data/v{API_VERSION}/connect/communities/{task_options_with_id['community_id']}",
                        "urlPathPrefix": "test",
                    }
                ],
                "total": "1",
            },
        )

        cc_task._init_task()
        with self.assertRaises(SalesforceException):
            cc_task._run_task()

    @responses.activate
    def test_throws_exception_for_bad_id(self):
        cc_task = create_task(PublishCommunity, task_options_with_id)
        community_publish_url = f"{cc_task.org_config.instance_url}/services/data/v{API_VERSION}/connect/communities/{task_options_with_id['community_id']}/publish"

        responses.add(
            method=responses.POST,
            url=community_publish_url,
            status=404,
            json=[
                {
                    "errorCode": "NOT_FOUND",
                    "message": "The requested resource does not exist",
                }
            ],
        )

        with self.assertRaises(SalesforceResourceNotFound):
            cc_task._init_task()
            cc_task._run_task()

    @responses.activate
    def test_throws_exception_for_unset_name_and_id(self):
        cc_task = create_task(PublishCommunity, {})

        cc_task._init_task()
        with self.assertRaises(TaskOptionsError):
            cc_task._run_task()
