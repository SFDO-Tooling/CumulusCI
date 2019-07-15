import json
import mock
import responses
import unittest
from datetime import datetime
from cumulusci.tasks.salesforce import CreateCommunity
from cumulusci.core.exceptions import SalesforceException
from .util import create_task


task_options = {
    "name": "Test Community",
    "description": "Community Details",
    "template": "VF Template",
    "url_path_prefix": "test",
}


class test_CreateCommunity(unittest.TestCase):
    @responses.activate
    def test_creates_community(self):
        cc_task = create_task(CreateCommunity, task_options)
        cc_task.sf = mock.Mock()
        cc_task.sf.restful.return_value = {
            "communities": [{"name": "Test Community", "id": "000000000000000"}]
        }
        frontdoor_url = "{}/secur/frontdoor.jsp?sid={}".format(
            cc_task.org_config.instance_url, cc_task.org_config.access_token
        )
        servlet_url = "{}/sites/servlet.SitePrerequisiteServlet".format(
            cc_task.org_config.instance_url
        )

        responses.add(method=responses.GET, url=frontdoor_url, status=200)
        responses.add(method=responses.GET, url=servlet_url, status=200)

        cc_task._run_task()

        self.assertEqual(2, len(responses.calls))
        self.assertEqual(frontdoor_url, responses.calls[0].request.url)
        self.assertEqual(servlet_url, responses.calls[1].request.url)
        cc_task.sf.restful.assert_any_call(
            "connect/communities",
            method="POST",
            data=json.dumps(
                {
                    "name": "Test Community",
                    "description": "Community Details",
                    "templateName": "VF Template",
                    "urlPathPrefix": "test",
                }
            ),
        )

    def test_waits_for_community_result__not_complete(self):
        cc_task = create_task(CreateCommunity, task_options)
        cc_task.sf = mock.Mock()
        cc_task.sf.restful.return_value = {"communities": []}
        cc_task.logger = mock.Mock()
        cc_task.time_start = datetime.now()

        cc_task._poll_action()

        self.assertFalse(cc_task.poll_complete)

    def test_waits_for_community_result__complete(self):
        cc_task = create_task(CreateCommunity, task_options)
        cc_task.sf = mock.Mock()
        cc_task.sf.restful.return_value = {
            "communities": [{"name": "Test Community", "id": "000000000000000"}]
        }
        cc_task.logger = mock.Mock()
        cc_task.time_start = datetime.now()

        cc_task._poll_action()

        self.assertTrue(cc_task.poll_complete)
        cc_task.logger.info.assert_called_once_with("Community 000000000000000 created")

    def test_throws_exception_for_timeout(self):
        cc_task = create_task(CreateCommunity, task_options)
        cc_task.sf = mock.Mock()

        cc_task.time_start = datetime(2019, 1, 1)
        with self.assertRaises(SalesforceException):
            cc_task._poll_action()

    @responses.activate
    def test_throws_exception_for_failed_prepare_step(self):
        cc_task = create_task(CreateCommunity, task_options)
        cc_task.sf = mock.Mock()
        cc_task.sf.restful.return_value = {
            "communities": [{"name": "Test Community", "id": "000000000000000"}]
        }
        frontdoor_url = "{}/secur/frontdoor.jsp?sid={}".format(
            cc_task.org_config.instance_url, cc_task.org_config.access_token
        )
        servlet_url = "{}/sites/servlet.SitePrerequisiteServlet".format(
            cc_task.org_config.instance_url
        )

        responses.add(method=responses.GET, url=frontdoor_url, status=200)
        responses.add(method=responses.GET, url=servlet_url, status=500)

        with self.assertRaises(SalesforceException):
            cc_task._run_task()
