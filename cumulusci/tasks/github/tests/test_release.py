import json
import unittest
from unittest import mock

import responses

from cumulusci.core.config import ServiceConfig, TaskConfig
from cumulusci.core.exceptions import GithubException, TaskOptionsError
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
            "test_alias",
            ServiceConfig(
                {
                    "username": "TestUser",
                    "token": "TestPass",
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
                        "version_id": "04t000000000000",
                        "dependencies": [{"namespace": "foo", "version": "1.0"}],
                        "package_type": "1GP",
                        "tag_prefix": "release/",
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
        # confirm the package_type was recorded in the tag message
        tag_request = json.loads(responses.calls._calls[3].request.body)
        assert "package_type: 1GP" in tag_request["message"]
        # confirm we didn't create a prerelease
        release_request = json.loads(responses.calls._calls[-1].request.body)
        assert not release_request["prerelease"]

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
            self.project_config,
            TaskConfig(
                {
                    "options": {
                        "version": "1.0",
                        "version_id": "04t000000000000",
                        "package_type": "1GP",
                        "tag_prefix": "release/",
                    }
                }
            ),
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

    @responses.activate
    def test_run_task__with_custom_prefix(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/releases/tags/custom/1.0",
            status=404,
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/refs/tags/custom/1.0",
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
                        "version_id": "04t000000000000",
                        "dependencies": [{"namespace": "foo", "version": "1.0"}],
                        "package_type": "2GP",
                        "tag_prefix": "custom/",
                    }
                }
            ),
        )
        task()
        self.assertEqual(
            {
                "tag_name": "custom/1.0",
                "name": "1.0",
                "dependencies": [{"namespace": "foo", "version": "1.0"}],
            },
            task.return_values,
        )
        assert "package_type: 2GP" in responses.calls._calls[3].request.body

    @responses.activate
    def test_run_task__beta_1gp(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/releases/tags/beta/1.0-Beta_1",
            status=404,
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/refs/tags/beta/1.0-Beta_1",
            status=404,
        )
        responses.add(
            method=responses.POST,
            url=self.repo_api_url + "/git/tags",
            json=self._get_expected_tag(
                "beta/1.0-Beta_1", "21e04cfe480f5293e2f7103eee8a5cbdb94f7982"
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
                        "version": "1.0 (Beta 1)",
                        "version_id": "04t000000000000",
                        "package_type": "1GP",
                        "tag_prefix": "beta/",
                    }
                }
            ),
        )
        task()
        self.assertEqual(
            {
                "tag_name": "beta/1.0-Beta_1",
                "name": "1.0 (Beta 1)",
                "dependencies": [],
            },
            task.return_values,
        )
        # confirm we didn't create a prerelease
        release_request = json.loads(responses.calls._calls[-1].request.body)
        assert release_request["prerelease"]

    @responses.activate
    def test_run_task__with_beta_2gp(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/releases/tags/beta/1.1",
            status=404,
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/refs/tags/beta/1.1",
            status=404,
        )
        responses.add(
            method=responses.POST,
            url=self.repo_api_url + "/git/tags",
            json=self._get_expected_tag(
                "release/1.1", "21e04cfe480f5293e2f7103eee8a5cbdb94f7982"
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
            match=[
                responses.json_params_matcher(
                    {
                        "tag_name": "beta/1.1",
                        "name": "1.1",
                        "draft": False,
                        "prerelease": True,
                    }
                )
            ],
            status=201,
        )

        task = CreateRelease(
            self.project_config,
            TaskConfig(
                {
                    "options": {
                        "version": "1.1",
                        "version_id": "04t000000000000",
                        "dependencies": [{"namespace": "foo", "version": "1.0"}],
                        "package_type": "2GP",
                        "tag_prefix": "beta/",
                    }
                }
            ),
        )
        task()
        self.assertEqual(
            {
                "tag_name": "beta/1.1",
                "name": "1.1",
                "dependencies": [{"namespace": "foo", "version": "1.0"}],
            },
            task.return_values,
        )
        assert "package_type: 2GP" in responses.calls._calls[3].request.body
