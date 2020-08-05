from datetime import datetime
import unittest

import pytz
import responses

from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.tasks.github import ReleaseReport
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tests.util import create_project_config


class TestReleaseReport(unittest.TestCase, GithubApiTestMixin):
    def setUp(self):
        self.repo_owner = "TestOwner"
        self.repo_name = "TestRepo"
        self.repo_api_url = "https://api.github.com/repos/{}/{}".format(
            self.repo_owner, self.repo_name
        )
        self.project_config = create_project_config(self.repo_name, self.repo_owner)
        self.project_config.keychain.set_service(
            "github",
            ServiceConfig(
                {
                    "username": "TestUser",
                    "password": "TestPass",
                    "email": "testuser@testdomain.com",
                }
            ),
        )

    @responses.activate
    def test_run_task(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/releases?per_page=100",
            json=[
                self._get_expected_release(
                    "rel/2.0",
                    created_at="2018-01-01T00:00:00Z",
                    url="https://api.github.com/repos/SalesforceFoundation/Cumulus/releases/2",
                    body="""Sandbox orgs:
Sandbox orgs: bogusdate
Sandbox orgs: 2018-08-01
Production orgs: 2018-09-01""",
                ),
                self._get_expected_release(
                    "rel/1.0",
                    created_at="2017-01-01T00:00:00Z",
                    url="https://api.github.com/repos/SalesforceFoundation/Cumulus/releases/1",
                ),
                self._get_expected_release(
                    "rel/3.0",
                    created_at="2019-01-01T00:00:00Z",
                    url="https://api.github.com/repos/SalesforceFoundation/Cumulus/releases/3",
                ),
                self._get_expected_release(
                    "beta/3.0-Beta_1",
                    prerelease=True,
                    created_at="2018-09-24T18:09:03Z",
                    url="https://api.github.com/repos/SalesforceFoundation/Cumulus/releases/4",
                ),
            ],
        )
        task = ReleaseReport(
            self.project_config,
            TaskConfig(
                {
                    "options": {
                        "date_start": "2018-01-01",
                        "date_end": "2018-12-31",
                        "print": True,
                    }
                }
            ),
        )
        task()
        self.assertEqual(
            [
                {
                    "beta": False,
                    "name": "release",
                    "tag": u"rel/2.0",
                    "time_created": datetime(2018, 1, 1, 0, 0, tzinfo=pytz.UTC),
                    "time_push_production": datetime(
                        2018, 9, 1, 0, 0, 0, 5, tzinfo=pytz.UTC
                    ),
                    "time_push_sandbox": datetime(
                        2018, 8, 1, 0, 0, 0, 2, tzinfo=pytz.UTC
                    ),
                    "url": "",
                }
            ],
            task.return_values["releases"],
        )
