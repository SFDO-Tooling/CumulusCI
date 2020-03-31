import os
from unittest import mock
import pytest
import responses
from datetime import datetime

from github3.repos.repo import Repository
from github3.pulls import ShortPullRequest
from github3.exceptions import ConnectionError
from github3.session import AppInstallationTokenAuth

from cumulusci.core import github
from cumulusci.core.exceptions import GithubException
from cumulusci.tasks.release_notes.tests.utils import MockUtil
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.core.github import (
    create_gist,
    get_github_api,
    validate_service,
    create_pull_request,
    markdown_link_to_pr,
    is_pull_request_merged,
    get_github_api_for_repo,
    is_label_on_pull_request,
    get_pull_requests_by_head,
    add_labels_to_pull_request,
    get_pull_requests_by_commit,
    get_pull_requests_with_base_branch,
)


class TestGithub(GithubApiTestMixin):
    @classmethod
    def teardown_method(cls):
        # clear cached repo -> installation mapping
        github.INSTALLATIONS.clear()

    @pytest.fixture
    def mock_util(self):
        return MockUtil("TestOwner", "TestRepo")

    @pytest.fixture
    def repo(self, gh_api):
        repo_json = self._get_expected_repo("TestOwner", "TestRepo")
        return Repository(repo_json, gh_api)

    def test_github_api_retries(self, mock_http_response):
        gh = get_github_api("TestUser", "TestPass")
        adapter = gh.session.get_adapter("http://")

        assert 0.3 == adapter.max_retries.backoff_factor
        assert 502 in adapter.max_retries.status_forcelist

        with mock.patch(
            "urllib3.connectionpool.HTTPConnectionPool._make_request"
        ) as _make_request:
            _make_request.side_effect = [
                mock_http_response(status=503),
                mock_http_response(status=200),
            ]

            gh.octocat("meow")
            assert 2 == _make_request.call_count

    @responses.activate
    @mock.patch("github3.apps.create_token")
    def test_get_github_api_for_repo(self, create_token):
        create_token.return_value = "ATOKEN"
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/installation",
            json={
                "id": 1,
                "access_tokens_url": "",
                "account": "",
                "app_id": "",
                "created_at": "",
                "events": "",
                "html_url": "",
                "permissions": "",
                "repositories_url": "",
                "repository_selection": "",
                "single_file_name": "",
                "target_id": "",
                "target_type": "",
                "updated_at": "",
            },
        )
        responses.add(
            "POST",
            "https://api.github.com/app/installations/1/access_tokens",
            status=201,
            json={"token": "ITOKEN", "expires_at": datetime.now().isoformat()},
        )

        with mock.patch.dict(
            os.environ, {"GITHUB_APP_KEY": "bogus", "GITHUB_APP_ID": "1234"}
        ):
            gh = get_github_api_for_repo(None, "TestOwner", "TestRepo")
            assert isinstance(gh.session.auth, AppInstallationTokenAuth)

    @responses.activate
    @mock.patch("github3.apps.create_token")
    def test_get_github_api_for_repo__not_installed(self, create_token):
        create_token.return_value = "ATOKEN"
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/installation",
            status=404,
        )
        with mock.patch.dict(
            os.environ, {"GITHUB_APP_KEY": "bogus", "GITHUB_APP_ID": "1234"}
        ):
            with pytest.raises(GithubException):
                get_github_api_for_repo(None, "TestOwner", "TestRepo")

    @responses.activate
    @mock.patch("cumulusci.core.github.GitHub")
    def test_get_github_api_for_repo__token(self, GitHub):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token"}):
            gh = get_github_api_for_repo(None, "TestOwner", "TestRepo")
        gh.login.assert_called_once_with(token="token")

    @responses.activate
    def test_validate_service(self):
        responses.add("GET", "https://api.github.com/rate_limit", status=401)
        with pytest.raises(GithubException):
            validate_service({"username": "BOGUS", "password": "BOGUS"})

    @responses.activate
    def test_get_pull_requests_by_head(self, mock_util, repo):
        self.init_github()
        mock_util.mock_pulls(
            pulls=self._get_expected_pull_requests(1),
            head=repo.owner.login + ":" + "some-other-branch",
        )
        pull_requests = get_pull_requests_by_head(repo, "some-other-branch")
        assert 1 == len(pull_requests)

        # ConnectionError present when we reachout with
        # a branch name (url parameter) that we aren't expecting
        with pytest.raises(ConnectionError):
            get_pull_requests_by_head(repo, "does-not-exist")

    @responses.activate
    def test_get_pull_requests_by_head__no_pulls(self, mock_util, repo):
        self.init_github()
        mock_util.mock_pulls()
        pull_requests = get_pull_requests_by_head(repo, "test_branch")
        assert pull_requests == []

        pull_requests = get_pull_requests_by_head(repo, "master")
        assert pull_requests is None

    @responses.activate
    def test_get_pull_request_by_head__multiple_pulls(self, mock_util, repo):
        self.init_github()
        mock_util.mock_pulls(pulls=self._get_expected_pull_requests(2))
        pull_requests = get_pull_requests_by_head(repo, "test_branch")
        assert 2 == len(pull_requests)

    @responses.activate
    def test_get_pull_requests_with_base_branch(self, mock_util, repo):
        self.init_github()
        mock_util.mock_pulls(base="master", head="TestOwner:some-branch")
        pull_requests = get_pull_requests_with_base_branch(
            repo, "master", head="some-branch"
        )
        assert 0 == len(pull_requests)

        responses.reset()
        mock_util.mock_pulls(pulls=self._get_expected_pull_requests(3), base="master")
        pull_requests = get_pull_requests_with_base_branch(repo, "master")
        assert 3 == len(pull_requests)

    @responses.activate
    def test_create_pull_request(self, mock_util, repo, gh_api):
        self.init_github()
        mock_util.mock_pulls(
            method=responses.POST,
            pulls=self._get_expected_pull_request(1, 1, "Test Body"),
        )
        pull_request = create_pull_request(repo, "test-branch")
        assert pull_request is not None
        assert pull_request.body == "Test Body"

    @responses.activate
    def test_is_label_on_pr(self, mock_util, repo, gh_api):
        self.init_github()
        mock_util.add_issue_response(self._get_expected_issue(1))
        mock_util.add_issue_response(self._get_expected_issue(2))
        mock_util.mock_issue_labels(1, responses.GET, ["Octocat", "bogus 1", "bogus 2"])
        mock_util.mock_issue_labels(2, responses.GET, ["bogus 1", "bogus 2"])

        pull_request = ShortPullRequest(self._get_expected_pull_request(1, 1), gh_api)
        pull_request.number = 1
        assert is_label_on_pull_request(repo, pull_request, "Octocat")
        pull_request.number = 2
        assert not is_label_on_pull_request(repo, pull_request, "Octocat")

    @responses.activate
    def test_add_labels_to_pull_request(self, mock_util, repo, gh_api):
        self.init_github()
        mock_util.add_issue_response(self._get_expected_issue(1))
        mock_util.mock_issue_labels(1, method=responses.POST)
        pull_request = ShortPullRequest(self._get_expected_pull_request(1, 1), gh_api)
        pull_request.number = 1

        add_labels_to_pull_request(repo, pull_request, "first", "second", "third")
        body = responses.calls[-1].request.body
        assert "first" in body
        assert "second" in body
        assert "third" in body

    @responses.activate
    def test_get_pull_request_by_commit(self, mock_util, repo, gh_api):
        self.init_github()
        commit_sha = "asdf1234asdf1234"
        mock_util.mock_pull_request_by_commit_sha(commit_sha)
        pull_requests = get_pull_requests_by_commit(gh_api, repo, commit_sha)
        assert len(pull_requests) == 1

    def test_is_pull_request_merged(self, gh_api):
        self.init_github()

        merged_pull_request = ShortPullRequest(
            self._get_expected_pull_request(1, 1), gh_api
        )
        merged_pull_request.merged_at = "DateTimeStr"

        unmerged_pull_request = ShortPullRequest(
            self._get_expected_pull_request(1, 1), gh_api
        )
        unmerged_pull_request.merged_at = None

        assert is_pull_request_merged(merged_pull_request)
        assert not is_pull_request_merged(unmerged_pull_request)

    def test_markdown_link_to_pr(self, gh_api):
        self.init_github()
        pr = ShortPullRequest(self._get_expected_pull_request(1, 1), gh_api)
        actual_link = markdown_link_to_pr(pr)
        expected_link = f"{pr.title} [[PR{pr.number}]({pr.html_url})]"

        assert expected_link == actual_link

    @responses.activate
    def test_create_gist(self, gh_api, mock_util):
        self.init_github()

        description = "Test Gist Creation"
        filename = "error_output.txt"
        content = "Hello there gist!"
        files = {filename: content}

        self.mock_gist(description, files)
        gist = create_gist(gh_api, description, files)

        expected_url = f"https://gist.github.com/{gist.id}"
        assert expected_url == gist.html_url

    def mock_gist(self, description, files):
        responses.add(
            method=responses.POST,
            url=f"https://api.github.com/gists",
            json=self._get_expected_gist(description, files),
            status=201,
        )
