# from unittest.mock import MagicMock, patch

import pytest

# import requests
import responses

import cumulusci.vcs.github.service as github
from cumulusci.core.config import ServiceConfig
from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tasks.release_notes.tests.utils import MockUtil
from cumulusci.tests.util import create_project_config
from cumulusci.vcs.github.adapter import GitHubRef, GitHubRepository, GitHubTag

# from github3.exceptions import NotFoundError
# from github3.git import Reference, Tag


class TestAdapter(GithubApiTestMixin):
    @classmethod
    def teardown_method(cls):
        # clear cached repo -> installation mapping
        github.INSTALLATIONS.clear()

    @pytest.fixture
    def mock_util(self):
        return MockUtil("TestOwner", "TestRepo")

    @pytest.fixture
    def project_config(self):
        project_config = create_project_config()

        return project_config

    @pytest.fixture
    @responses.activate
    def repo(self, gh_api, project_config, mock_util):
        mock_util.mock_get_repo()
        git_repo = GitHubRepository(gh_api, project_config)
        return git_repo

    @responses.activate
    def test_get_ref_for_tag(self, repo):
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/tag_SHA",
            json=self._get_expected_tag_ref("tag_SHA", "tag_SHA"),
            status=200,
        )
        ref = repo.get_ref_for_tag("tag_SHA")
        assert ref.sha == "tag_SHA"
        assert isinstance(ref, GitHubRef)

    @responses.activate
    def test_get_ref_for_tag__404(self, repo):
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/tag_SHA",
            json=self._get_expected_tag_ref("tag_SHA", "tag_SHA"),
            status=404,
        )
        with pytest.raises(GithubApiNotFoundError):
            repo.get_ref_for_tag("tag_SHA")

    @responses.activate
    def test_get_tag_by_ref(self, repo, gh_api, mock_util):
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/tag_SHA",
            json=self._get_expected_tag_ref("tag_SHA", "tag_SHA"),
            status=200,
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/tags/tag_SHA",
            json=self._get_expected_tag("beta/1.0", "tag_SHA", "tag_SHA"),
            status=200,
        )
        ref = repo.get_ref_for_tag("tag_SHA")

        tag = repo.get_tag_by_ref(ref, "beta/1.0")
        assert isinstance(tag, GitHubTag)
        assert tag.sha == "tag_SHA"

    @responses.activate
    def test_get_tag_by_ref__404(self, repo):
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/tag_SHA",
            json=self._get_expected_tag_ref("tag_SHA", "tag_SHA"),
            status=200,
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/tags/tag_SHA",
            json=self._get_expected_tag("beta/1.0", "tag_SHA", "tag_SHA"),
            status=404,
        )
        ref = repo.get_ref_for_tag("tag_SHA")

        with pytest.raises(GithubApiNotFoundError):
            repo.get_tag_by_ref(ref, "beta/1.0")

    @responses.activate
    def test_create_tag_success(self, repo, project_config):
        self.init_github()
        project_config.keychain.set_service(
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
        responses.add(
            responses.POST,
            self.repo_api_url + "/git/tags",
            json=self._get_expected_tag("release/1.0", "SHA", "SHA"),
            status=201,
        )
        responses.add(
            responses.POST, self.repo_api_url + "/git/refs", json={}, status=201
        )

        tag = repo.create_tag(
            tag_name="v1.0.0",
            message="Test tag",
            sha="test_sha",
            obj_type="commit",
            tagger={"name": "custom_user", "email": "custom_user@example.com"},
        )

        assert isinstance(tag, GitHubTag)
        assert tag.sha == "SHA"
