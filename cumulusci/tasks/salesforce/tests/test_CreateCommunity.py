import json
from unittest import mock
import responses
import unittest
from datetime import datetime
from cumulusci.tasks.salesforce import CreateCommunity
from cumulusci.core.exceptions import SalesforceException
from simple_salesforce.exceptions import SalesforceMalformedRequest
from .util import create_task


task_options = {
    "name": "Test Community",
    "description": "Community Details",
    "template": "VF Template",
    "url_path_prefix": "test",
}
task_options_no_url_path_prefix = {
    "name": "Test Community",
    "description": "Community Details",
    "template": "VF Template",
}


class test_CreateCommunity(unittest.TestCase):
    @responses.activate
    def test_creates_community(self):
        cc_task = create_task(CreateCommunity, task_options)
        community_url = "{}/services/data/v48.0/connect/communities".format(
            cc_task.org_config.instance_url
        )

        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": []},
        )
        responses.add(method=responses.POST, url=community_url, status=200, json={})
        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": [{"name": "Test Community", "id": "000000000000000"}]},
        )

        cc_task()

        self.assertEqual(3, len(responses.calls))
        self.assertEqual(community_url, responses.calls[1].request.url)
        self.assertEqual(community_url, responses.calls[2].request.url)
        self.assertEqual(
            json.dumps(
                {
                    "name": "Test Community",
                    "description": "Community Details",
                    "templateName": "VF Template",
                    "urlPathPrefix": "test",
                }
            ),
            responses.calls[1].request.body,
        )

    @responses.activate
    def test_creates_community_no_url_path_prefix(self):
        cc_task = create_task(CreateCommunity, task_options_no_url_path_prefix)
        community_url = "{}/services/data/v48.0/connect/communities".format(
            cc_task.org_config.instance_url
        )

        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": []},
        )
        responses.add(method=responses.POST, url=community_url, status=200, json={})
        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": [{"name": "Test Community", "id": "000000000000000"}]},
        )

        cc_task()

        self.assertEqual(3, len(responses.calls))
        self.assertEqual(community_url, responses.calls[1].request.url)
        self.assertEqual(community_url, responses.calls[2].request.url)
        self.assertEqual(
            json.dumps(
                {
                    "name": "Test Community",
                    "description": "Community Details",
                    "templateName": "VF Template",
                    "urlPathPrefix": "",
                }
            ),
            responses.calls[1].request.body,
        )

    @responses.activate
    def test_error_for_existing_community(self):
        cc_task = create_task(CreateCommunity, task_options)
        community_url = "{}/services/data/v48.0/connect/communities".format(
            cc_task.org_config.instance_url
        )

        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": [{"name": "Test Community", "id": "000000000000000"}]},
        )

        with self.assertRaises(Exception):
            cc_task()

    @responses.activate
    def test_handles_community_created_between_tries(self):
        cc_task = create_task(CreateCommunity, task_options)
        community_url = "{}/services/data/v48.0/connect/communities".format(
            cc_task.org_config.instance_url
        )

        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": []},
        )
        responses.add(
            method=responses.POST,
            url=community_url,
            status=400,
            json=[
                {
                    "errorCode": "INVALID_INPUT",
                    "message": "Error: A Community with this name already exists.",
                }
            ],
        )
        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": [{"name": "Test Community", "id": "000000000000000"}]},
        )

        cc_task()

    @responses.activate
    def test_throws_exception_for_existing_url_path_prefix(self):
        cc_task = create_task(CreateCommunity, task_options)
        community_url = "{}/services/data/v48.0/connect/communities".format(
            cc_task.org_config.instance_url
        )

        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": []},
        )
        responses.add(
            method=responses.POST,
            url=community_url,
            status=400,
            json=[
                {
                    "errorCode": "INVALID_INPUT",
                    "message": "That URL is already in use. Please enter a unique one.",
                }
            ],
        )

        cc_task._init_task()
        with self.assertRaises(SalesforceMalformedRequest):
            cc_task._run_task()()

    @responses.activate
    def test_throws_exception_for_existing_no_url_path_prefix(self):
        cc_task = create_task(CreateCommunity, task_options_no_url_path_prefix)
        community_url = "{}/services/data/v48.0/connect/communities".format(
            cc_task.org_config.instance_url
        )

        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": []},
        )
        responses.add(
            method=responses.POST,
            url=community_url,
            status=400,
            json=[
                {
                    "errorCode": "INVALID_INPUT",
                    "message": "Enter a URL for your community.",
                }
            ],
        )

        cc_task._init_task()
        with self.assertRaises(SalesforceMalformedRequest):
            cc_task._run_task()()

    @responses.activate
    def test_waits_for_community_result__not_complete(self):
        cc_task = create_task(CreateCommunity, task_options)

        community_url = "{}/services/data/v48.0/connect/communities".format(
            cc_task.org_config.instance_url
        )
        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": []},
        )

        cc_task._init_task()
        cc_task.time_start = datetime.now()
        cc_task._poll_action()

        self.assertFalse(cc_task.poll_complete)

    @responses.activate
    def test_waits_for_community_result__complete(self):
        cc_task = create_task(CreateCommunity, task_options)
        community_url = "{}/services/data/v48.0/connect/communities".format(
            cc_task.org_config.instance_url
        )
        responses.add(
            method=responses.GET,
            url=community_url,
            status=200,
            json={"communities": [{"name": "Test Community", "id": "000000000000000"}]},
        )
        cc_task.logger = mock.Mock()

        cc_task._init_task()
        cc_task.time_start = datetime.now()
        cc_task._poll_action()

        self.assertTrue(cc_task.poll_complete)
        cc_task.logger.info.assert_called_once_with("Community 000000000000000 created")

    def test_throws_exception_for_timeout(self):
        cc_task = create_task(CreateCommunity, task_options)

        cc_task.time_start = datetime(2019, 1, 1)
        with self.assertRaises(SalesforceException):
            cc_task._poll_action()
