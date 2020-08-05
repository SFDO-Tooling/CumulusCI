from unittest import mock
import unittest

import responses

from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import GithubException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.github import CreateRelease
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tests.util import create_project_config


@mock.patch("cumulusci.tasks.github.release.time.sleep", mock.Mock())
class TestCreateRelease(unittest.TestCase, GithubApiTestMixin):
    def setUp(self):
        self.repo_owner = "TestOwner"
        self.repo_name = "TestRepo"
        self.repo_api_url = "https://api.github.com/repos/{}/{}".format(
            self.repo_owner, self.repo_name
        )
        self.project_config = create_project_config(
            self.repo_name,
            self.repo_owner,
            repo_commit="21e04cfe480f5293e2f7103eee8a5cbdb94f7982",
        )
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
            url=self.repo_api_url + "/releases/tags/release/1.0",
            status=404,
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/refs/tags/release/1.0",
            status=404,
        )
        responses.add(
            method=responses.POST,
            url=self.repo_api_url + "/git/tags",
            json=self._get_expected_tag(
                "release/1.0", "21e04cfe480f5293e2f7103eee8a5cbdb94f7982"
            ),
            status=201,
        )
        responses.add(
            method=responses.POST,
            url=self.repo_api_url + "/git/refs",
            json={},
            status=201,
        )
        responses.add(
            method=responses.POST,
            url=self.repo_api_url + "/releases",
            json=self._get_expected_release("release"),
            status=201,
        )

        task = CreateRelease(
            self.project_config,
            TaskConfig(
                {
                    "options": {
                        "version": "1.0",
                        "dependencies": [{"namespace": "foo", "version": "1.0"}],
                    }
                }
            ),
        )
        task()
        self.assertEqual(
            {
                "tag_name": "release/1.0",
                "name": "1.0",
                "dependencies": [{"namespace": "foo", "version": "1.0"}],
            },
            task.return_values,
        )

    @responses.activate
    def test_run_task__release_already_exists(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/releases/tags/release/1.0",
            json=self._get_expected_release("release/1.0"),
        )

        task = CreateRelease(
            self.project_config, TaskConfig({"options": {"version": "1.0"}})
        )
        with self.assertRaises(GithubException):
            task()

    @responses.activate
    def test_run_task__no_commit(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/releases/tags/release/1.0",
            status=404,
        )
        del self.project_config._repo_info["commit"]

        with self.assertRaises(GithubException):
            CreateRelease(
                self.project_config,
                TaskConfig({"options": {"version": "1.0", "commit": None}}),
            )

    @responses.activate
    def test_run_task__short_commit(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/releases/tags/release/1.0",
            status=404,
        )
        self.project_config._repo_info["commit"] = "too_short"

        with self.assertRaises(TaskOptionsError):
            CreateRelease(
                self.project_config, TaskConfig({"options": {"version": "1.0"}})
            )
