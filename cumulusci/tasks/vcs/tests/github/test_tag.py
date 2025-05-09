import pytest
import responses

from cumulusci.core.config import ServiceConfig, TaskConfig
from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tasks.vcs import CloneTag
from cumulusci.tests.util import create_project_config


class TestCloneTag(GithubApiTestMixin):
    def setup_method(self):
        self.repo_owner = "TestOwner"
        self.repo_name = "TestRepo"
        self.repo_api_url = "https://api.github.com/repos/{}/{}".format(
            self.repo_owner, self.repo_name
        )
        self.project_config = create_project_config(self.repo_name, self.repo_owner)
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
            responses.GET,
            self.repo_api_url + "/git/ref/tags/beta/1.0-Beta_1",
            json={
                "object": {"sha": "SHA", "url": "", "type": "tag"},
                "url": "",
                "ref": "refs/tags/beta/1.0-Beta_1",
            },
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/git/tags/SHA",
            json=self._get_expected_tag("beta/1.0-Beta_1", "SHA"),
        )
        responses.add(
            responses.POST,
            self.repo_api_url + "/git/tags",
            json=self._get_expected_tag("release/1.0", "SHA"),
            status=201,
        )
        responses.add(
            responses.POST, self.repo_api_url + "/git/refs", json={}, status=201
        )
        task_config = TaskConfig(
            {"options": {"src_tag": "beta/1.0-Beta_1", "tag": "release/1.0"}}
        )
        task = CloneTag(self.project_config, task_config)
        task()
        assert task.result.tag.tag == "release/1.0"

    @responses.activate
    def test_run_task__tag_not_found(self):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/git/ref/tags/beta/1.0-Beta_1",
            json={
                "object": {"sha": "SHA", "url": "", "type": "tag"},
                "url": "",
                "ref": "tags/beta/1.0-Beta_1",
            },
        )
        responses.add(responses.GET, self.repo_api_url + "/git/tags/SHA", status=404)
        task_config = TaskConfig(
            {"options": {"src_tag": "beta/1.0-Beta_1", "tag": "release/1.0"}}
        )
        task = CloneTag(self.project_config, task_config)
        with pytest.raises(GithubApiNotFoundError):
            task()
