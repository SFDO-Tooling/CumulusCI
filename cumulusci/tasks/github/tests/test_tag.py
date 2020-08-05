import pytest
import responses as responses_lib

from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import GithubException
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.github.tag import CloneTag
from cumulusci.tasks.github.tag import CreateTag
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tests.util import create_project_config


@pytest.fixture
def responses():
    with responses_lib.RequestsMock() as mocked:
        yield mocked


@pytest.mark.usefixtures("responses")
class TestCreateTag(GithubApiTestMixin):
    def setup_method(self, method):
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

    def test_run_task(self, responses):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/git/refs/tags/something",
            status=404,
        )
        responses.add(
            method=responses.POST,
            url=self.repo_api_url + "/git/tags",
            json=self._get_expected_tag(
                "something", "21e04cfe480f5293e2f7103eee8a5cbdb94f7982"
            ),
            status=201,
        )
        responses.add(
            method=responses.POST,
            url=self.repo_api_url + "/git/refs",
            json={},
            status=201,
        )

        task = CreateTag(
            self.project_config, TaskConfig({"options": {"tag": "something"}})
        )
        task()

    def test_init_options__no_commit(self):
        del self.project_config._repo_info["commit"]

        with pytest.raises(GithubException):
            CreateTag(
                self.project_config,
                TaskConfig({"options": {"tag": "something", "commit": None}}),
            )

    def test_init_options__short_commit(self):
        self.project_config._repo_info["commit"] = "too_short"

        with pytest.raises(TaskOptionsError):
            CreateTag(
                self.project_config, TaskConfig({"options": {"tag": "something"}})
            )


@pytest.mark.usefixtures("responses")
class TestCloneTag(GithubApiTestMixin):
    def setup_method(self, method):
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

    def test_run_task(self, responses):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/git/refs/tags/beta/1.0-Beta_1",
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
        assert task.result.tag == "release/1.0"

    def test_run_task__tag_not_found(self, responses):
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo(owner=self.repo_owner, name=self.repo_name),
        )
        responses.add(
            responses.GET,
            self.repo_api_url + "/git/refs/tags/beta/1.0-Beta_1",
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
        with pytest.raises(GithubException):
            task()
