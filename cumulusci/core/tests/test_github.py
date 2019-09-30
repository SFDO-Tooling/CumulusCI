import io
import os
import mock
import pytest
import responses
from datetime import datetime
from http.client import HTTPMessage

from github3.repos.repo import Repository
from github3.pulls import ShortPullRequest
from github3.exceptions import ConnectionError
from github3.session import AppInstallationTokenAuth

from cumulusci.core import github
from cumulusci.core.exceptions import GithubException
from cumulusci.tasks.release_notes.tests.utils import MockUtil
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.core.github import (
    get_github_api,
    validate_service,
    create_pull_request,
    get_github_api_for_repo,
    is_label_on_pull_request,
    get_pull_requests_by_head,
    add_labels_to_pull_request,
    get_pull_requests_with_base_branch,
)


class MockHttpResponse(mock.Mock):
    def __init__(self, status):
        super(MockHttpResponse, self).__init__()
        self.status = status
        self.strict = 0
        self.version = 0
        self.reason = None
        self.msg = HTTPMessage(io.BytesIO())
        self.closed = True

    def read(self):
        return b""

    def isclosed(self):
        return self.closed


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

    @mock.patch("urllib3.connectionpool.HTTPConnectionPool._make_request")
    def test_github_api_retries(self, _make_request):
        gh = get_github_api("TestUser", "TestPass")
        adapter = gh.session.get_adapter("http://")

        assert 0.3 == adapter.max_retries.backoff_factor
        assert 502 in adapter.max_retries.status_forcelist

        _make_request.side_effect = [
            MockHttpResponse(status=503),
            MockHttpResponse(status=200),
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
