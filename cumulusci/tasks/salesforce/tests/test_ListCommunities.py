# -*- coding: utf-8 -*-
import responses
import unittest
from cumulusci.tasks.salesforce import ListCommunities
from .util import create_task


task_options = {}


class test_ListCommunities(unittest.TestCase):
    @responses.activate
    def test_lists_community(self):
        cc_task = create_task(ListCommunities, task_options)
        communities_url = "{}/services/data/v46.0/connect/communities".format(
            cc_task.org_config.instance_url
        )

        community_id = "000000000000000000"
        community_name = "Test Community"
        community_url_prefix = "test"
        community2_id = "000000000000000001"
        community2_name = "Test Community Д Two"

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
                        "id": "{}".format(community_id),
                        "invitationsEnabled": "false",
                        "knowledgeableEnabled": "false",
                        "loginUrl": "https://mydomain.force.com/{}/s/login".format(
                            community_url_prefix
                        ),
                        "memberVisibilityEnabled": "true",
                        "name": "{}".format(community_name),
                        "nicknameDisplayEnabled": "false",
                        "privateMessagesEnabled": "false",
                        "reputationEnabled": "false",
                        "sendWelcomeEmail": "true",
                        "siteAsContainerEnabled": "true",
                        "siteUrl": "https://mydomain.force.com/{}".format(
                            community_url_prefix
                        ),
                        "status": "Live",
                        "templateName": "VF Template",
                        "url": "/services/data/v46.0/connect/communities/{}".format(
                            community_id
                        ),
                        "urlPathPrefix": "{}".format(community_url_prefix),
                    },
                    {
                        "allowChatterAccessWithoutLogin": "false",
                        "allowMembersToFlag": "false",
                        "description": "This is a test community",
                        "id": "{}".format(community2_id),
                        "invitationsEnabled": "false",
                        "knowledgeableEnabled": "false",
                        "loginUrl": "https://mydomain.force.com/s/login",
                        "memberVisibilityEnabled": "true",
                        "name": "{}".format(community2_name),
                        "nicknameDisplayEnabled": "false",
                        "privateMessagesEnabled": "false",
                        "reputationEnabled": "false",
                        "sendWelcomeEmail": "true",
                        "siteAsContainerEnabled": "true",
                        "siteUrl": "https://mydomain.force.com/",
                        "status": "Live",
                        "templateName": "VF Template",
                        "url": "/services/data/v46.0/connect/communities/{}".format(
                            community2_id
                        ),
                        "urlPathPrefix": None,
                    },
                ],
                "total": "2",
            },
        )

        cc_task()

        self.assertEqual(1, len(responses.calls))
        self.assertEqual(communities_url, responses.calls[0].request.url)
