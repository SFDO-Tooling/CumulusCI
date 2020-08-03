import unittest
from unittest import mock
import json

import pytest
import responses

from cumulusci.core.config import ServiceConfig, TaskConfig
from cumulusci.core.exceptions import GithubException
from cumulusci.tasks.github.publish import PublishSubtree
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tests.util import create_project_config


class TestPublishSubtree(unittest.TestCase, GithubApiTestMixin):
    def setUp(self):
        self.repo_owner = "TestOwner"
        self.repo_name = "TestRepo"
        self.repo_api_url = (
            f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        )

        self.public_owner = "TestOwner"
        self.public_name = "PublicRepo"
        self.public_repo_url = (
            f"https://api.github.com/repos/{self.public_owner}/{self.public_name}"
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

    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_run_task(self, commit_dir, extract_github):
        with responses.RequestsMock() as rsps:
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url,
                json=self._get_expected_repo(
                    owner=self.repo_owner, name=self.repo_name
                ),
            )
            rsps.add(
                responses.GET,
                self.repo_api_url + "/releases/latest",
                json=self._get_expected_release("release/1.0"),
            )
            rsps.add(
                method=responses.GET,
                url=self.public_repo_url,
                json=self._get_expected_repo(
                    owner=self.public_owner, name=self.public_name
                ),
            )
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url + "/git/refs/tags/release/1.0",
                status=200,
                json=self._get_expected_tag_ref("release/1.0", "SHA"),
            )
            rsps.add(
                method=responses.GET,
                url=self.repo_api_url + "/git/tags/SHA",
                json=self._get_expected_tag("release/1.0", "SHA"),
                status=200,
            )
            rsps.add(
                responses.GET,
                self.repo_api_url + "/releases/tags/release/1.0",
                json=self._get_expected_release("release/1.0"),
            )
            rsps.add(
                responses.GET,
                self.public_repo_url + "/git/refs/tags/release/1.0",
                status=404,
            )
            rsps.add(
                responses.POST,
                self.public_repo_url + "/releases",
                json=self._get_expected_release("release"),
            )
            task_config = TaskConfig(
                {
                    "options": {
                        "branch": "master",
                        "version": "latest",
                        "repo_url": self.public_repo_url,
                        "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                    }
                }
            )
            extract_github.return_value.namelist.return_value = [
                "tasks/foo.py",
                "unpackaged/pre/foo/package.xml",
                "force-app",
            ]

            task = PublishSubtree(self.project_config, task_config)
            task()

            expected_release_body = json.dumps(
                {
                    "tag_name": "release/1.0",
                    "name": "1.0",
                    "body": "",
                    "draft": False,
                    "prerelease": False,
                }
            )
            create_release_call = rsps.calls[9]
            assert create_release_call.request.url == self.public_repo_url + "/releases"
            assert create_release_call.request.method == responses.POST
            assert create_release_call.request.body == expected_release_body

    @responses.activate
    @mock.patch("cumulusci.core.config.project_config.BaseProjectConfig.get_latest_tag")
    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir.__call__")
    def test_run_task_latest_beta(self, commit_dir, download, get_tag):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url,
            json=self._get_expected_repo(
                owner=self.public_owner, name=self.public_name
            ),
        )
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "version": "latest_beta",
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        get_tag.return_value = "beta/1.0_Beta_1"
        commit_dir.return_value = None
        task = PublishSubtree(self.project_config, task_config)
        task()
        get_tag.assert_called_once_with(True)

    @responses.activate
    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_ref_not_found(self, commit_dir, extract_github):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url,
            json=self._get_expected_repo(
                owner=self.public_owner, name=self.public_name
            ),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/refs/tags/release/1.0",
            status=404,
        )
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "version": "latest",
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        extract_github.return_value.namelist.return_value = [
            "tasks/foo.py",
            "unpackaged/pre/foo/package.xml",
            "force-app",
        ]
        task = PublishSubtree(self.project_config, task_config)
        with pytest.raises(GithubException) as exc:
            task()
        assert "Ref not found for tag release/1.0" == str(exc.value)

    @responses.activate
    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_tag_not_found(self, commit_dir, extract_github):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url,
            json=self._get_expected_repo(
                owner=self.public_owner, name=self.public_name
            ),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/refs/tags/release/1.0",
            status=201,
            json=self._get_expected_tag_ref("release/1.0", "SHA"),
        )
        responses.add(
            responses.GET,
            self.public_repo_url + "/releases/tags/release/1.0",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            method=responses.GET, url=self.repo_api_url + "/git/tags/SHA", status=404
        )
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "version": "latest",
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        extract_github.return_value.namelist.return_value = [
            "tasks/foo.py",
            "unpackaged/pre/foo/package.xml",
            "force-app",
        ]
        task = PublishSubtree(self.project_config, task_config)
        with pytest.raises(GithubException) as exc:
            task()
        assert "Tag release/1.0 not found" == str(exc.value)

    @responses.activate
    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_release_not_found(self, commit_dir, extract_github):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url,
            json=self._get_expected_repo(
                owner=self.public_owner, name=self.public_name
            ),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/refs/tags/release/1.0",
            status=200,
            json=self._get_expected_tag_ref("release/1.0", "SHA"),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/tags/SHA",
            json=self._get_expected_tag("release/1.0", "SHA"),
            status=200,
        )
        responses.add(
            responses.GET, self.repo_api_url + "/releases/tags/release/1.0", status=404
        )
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "version": "latest",
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        extract_github.return_value.namelist.return_value = [
            "tasks/foo.py",
            "unpackaged/pre/foo/package.xml",
            "force-app",
        ]
        task = PublishSubtree(self.project_config, task_config)
        with pytest.raises(GithubException) as exc:
            task()
        assert "Release for release/1.0 not found" == str(exc.value)

    @responses.activate
    @mock.patch("cumulusci.tasks.github.publish.download_extract_github_from_repo")
    @mock.patch("cumulusci.tasks.github.publish.CommitDir")
    def test_target_release_exists(self, commit_dir, extract_github):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/releases/latest",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url,
            json=self._get_expected_repo(
                owner=self.public_owner, name=self.public_name
            ),
        )
        responses.add(
            method=responses.GET,
            url=self.public_repo_url + "/git/refs/tags/release/1.0",
            status=201,
            json=self._get_expected_tag_ref("release/1.0", "SHA"),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/refs/tags/release/1.0",
            status=201,
            json=self._get_expected_tag_ref("release/1.0", "SHA"),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/tags/SHA",
            json=self._get_expected_tag("release/1.0", "SHA"),
            status=201,
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/releases/tags/release/1.0",
            json=self._get_expected_release("release/1.0"),
        )
        responses.add(
            responses.GET,
            self.public_repo_url + "/releases/tags/release/1.0",
            json=self._get_expected_release("release/1.0"),
        )
        task_config = TaskConfig(
            {
                "options": {
                    "branch": "master",
                    "version": "latest",
                    "repo_url": self.public_repo_url,
                    "includes": ["tasks/foo.py", "unpackaged/pre/foo/package.xml"],
                }
            }
        )
        extract_github.return_value.namelist.return_value = [
            "tasks/foo.py",
            "unpackaged/pre/foo/package.xml",
            "force-app",
        ]
        task = PublishSubtree(self.project_config, task_config)
        with pytest.raises(GithubException) as exc:
            task()
        assert "Ref for tag release/1.0 already exists in target repo" == str(exc.value)
