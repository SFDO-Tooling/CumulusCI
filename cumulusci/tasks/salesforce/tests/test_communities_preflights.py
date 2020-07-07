import unittest

from cumulusci.tasks.salesforce.communities_preflights import IsCommunitiesEnabled
from .util import create_task

import responses


class TestCommunitiesPreflights(unittest.TestCase):
    @responses.activate
    def test_community_preflight__positive(self):
        task = create_task(IsCommunitiesEnabled, {})

        responses.add("GET", task.org_config.start_url, status=200)
        responses.add(
            "GET",
            "{}/sites/servlet.SitePrerequisiteServlet".format(
                task.org_config.instance_url
            ),
            status=200,
        )

        task()

        assert task.return_values is True

    @responses.activate
    def test_community_preflight__negative(self):
        task = create_task(IsCommunitiesEnabled, {})

        responses.add("GET", task.org_config.start_url, status=200)
        responses.add(
            "GET",
            "{}/sites/servlet.SitePrerequisiteServlet".format(
                task.org_config.instance_url
            ),
            status=500,
        )

        task()

        assert task.return_values is False
