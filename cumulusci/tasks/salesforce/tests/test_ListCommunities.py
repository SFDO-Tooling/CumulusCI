# -*- coding: utf-8 -*-


import responses

from cumulusci.tasks.salesforce import ListCommunities

from .util import create_task

task_options = {}


class TestListCommunities:
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
                        "id": community_id,
                        "invitationsEnabled": "false",
                        "knowledgeableEnabled": "false",
                        "loginUrl": f"https://mydomain.force.com/{community_url_prefix}/s/login",
                        "memberVisibilityEnabled": "true",
                        "name": community_name,
                        "nicknameDisplayEnabled": "false",
                        "privateMessagesEnabled": "false",
                        "reputationEnabled": "false",
                        "sendWelcomeEmail": "true",
                        "siteAsContainerEnabled": "true",
                        "siteUrl": f"https://mydomain.force.com/{community_url_prefix}",
                        "status": "Live",
                        "templateName": "VF Template",
                        "url": f"/services/data/v46.0/connect/communities/{community_id}",
                        "urlPathPrefix": community_url_prefix,
                    },
                    {
                        "allowChatterAccessWithoutLogin": "false",
                        "allowMembersToFlag": "false",
                        "description": "This is a test community",
                        "id": community2_id,
                        "invitationsEnabled": "false",
                        "knowledgeableEnabled": "false",
                        "loginUrl": "https://mydomain.force.com/s/login",
                        "memberVisibilityEnabled": "true",
                        "name": community2_name,
                        "nicknameDisplayEnabled": "false",
                        "privateMessagesEnabled": "false",
                        "reputationEnabled": "false",
                        "sendWelcomeEmail": "true",
                        "siteAsContainerEnabled": "true",
                        "siteUrl": "https://mydomain.force.com/",
                        "status": "Live",
                        "templateName": "VF Template",
                        "url": f"/services/data/v46.0/connect/communities/{community2_id}",
                        "urlPathPrefix": None,
                    },
                ],
                "total": "2",
            },
        )

        cc_task()

        assert 1 == len(responses.calls)
        assert communities_url == responses.calls[0].request.url
        assert cc_task.return_values == [community_name, community2_name]
