import json
import os
from datetime import datetime
from ssl import SSLCertVerificationError
from unittest import mock

import pytest
import requests
import responses
from github3 import GitHub, GitHubEnterprise
from github3.exceptions import (
    AuthenticationFailed,
    ConnectionError,
    ForbiddenError,
    ResponseError,
    TransportError,
)
from github3.pulls import ShortPullRequest
from github3.repos.repo import Repository
from github3.session import AppInstallationTokenAuth
from requests.exceptions import RequestException, RetryError, SSLError
from requests.models import Response

import cumulusci
from cumulusci.core import github
from cumulusci.core.config import BaseProjectConfig, ServiceConfig, UniversalConfig
from cumulusci.core.exceptions import (
    DependencyLookupError,
    GithubApiError,
    GithubApiNotFoundError,
    GithubException,
    ServiceNotConfigured,
)
from cumulusci.core.github import (
    SELF_SIGNED_WARNING,
    SSO_WARNING,
    UNAUTHORIZED_WARNING,
    _determine_github_client,
    add_labels_to_pull_request,
    catch_common_github_auth_errors,
    check_github_sso_auth,
    create_gist,
    create_pull_request,
    format_github3_exception,
    get_auth_from_service,
    get_commit,
    get_github_api,
    get_github_api_for_repo,
    get_latest_prerelease,
    get_oauth_device_flow_token,
    get_oauth_scopes,
    get_pull_requests_by_commit,
    get_pull_requests_by_head,
    get_pull_requests_with_base_branch,
    get_ref_for_tag,
    get_sso_disabled_orgs,
    get_tag_by_name,
    get_version_id_from_tag,
    is_label_on_pull_request,
    is_pull_request_merged,
    markdown_link_to_pr,
    request_url_from_exc,
    validate_gh_enterprise,
    validate_service,
    warn_oauth_restricted,
)
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tasks.release_notes.tests.utils import MockUtil


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

    @pytest.fixture
    def keychain_enterprise(self):
        runtime = mock.Mock()
        runtime.project_config = BaseProjectConfig(UniversalConfig(), config={})
        runtime.keychain = BaseProjectKeychain(runtime.project_config, None)
        runtime.keychain.set_service(
            "github_enterprise",
            "ent",
            ServiceConfig(
                {
                    "username": "testusername",
                    "email": "test@domain.com",
                    "token": "ATOKEN",
                    "server_domain": "git.enterprise.domain.com",
                }
            ),
        )
        return runtime.keychain

    def test_github_api_retries__escape_hatch_SSL_error(self):
        gh = get_github_api("TestUser", "TestPass")
        adapter = gh.session.get_adapter("http://")

        assert 0.3 == adapter.max_retries.backoff_factor
        assert 502 in adapter.max_retries.status_forcelist

        with mock.patch(
            "urllib3.connectionpool.HTTPConnectionPool._make_request"
        ) as _make_request:
            _make_request.side_effect = SSLCertVerificationError(
                "SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate in certificate chain"
            )

            with pytest.raises(
                ConnectionError,
                match="(CERTIFICATE_VERIFY_FAILED)",
            ):
                gh.octocat("meow")

            assert 1 == _make_request.call_count

    def test_github_api_retries(self):
        gh = get_github_api("TestUser", "TestPass")
        adapter = gh.session.get_adapter("http://")

        assert 0.3 == adapter.max_retries.backoff_factor
        assert 502 in adapter.max_retries.status_forcelist

        user_json = {
            "login": "TestUser",
            "id": 123456,
            "type": "User",
            "url": "https://api.github.com/user",
            "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4",
            "events_url": "https://api.github.com/users/TestUser/events{/privacy}",
            "followers_url": "https://api.github.com/users/TestUser/followers",
            "following_url": "https://api.github.com/users/TestUser/following{/other_user}",
            "gists_url": "https://api.github.com/users/TestUser/gists{/gist_id}",
            "gravatar_id": "",
            "html_url": "https://github.com/TestUser",
            "organizations_url": "https://api.github.com/users/TestUser/orgs",
            "received_events_url": "https://api.github.com/users/TestUser/received_events",
            "repos_url": "https://api.github.com/users/TestUser/repos",
            "site_admin": False,
            "starred_url": "https://api.github.com/users/TestUser/starred{/owner}{/repo}",
            "subscriptions_url": "https://api.github.com/users/TestUser/subscriptions",
            "bio": "Test bio",
            "blog": "https://testuserblog.com",
            "company": "Test Company",
            "created_at": "2020-01-01T00:00:00Z",
            "email": "testuser@example.com",
            "followers": 10,
            "following": 5,
            "hireable": True,
            "location": "Test City",
            "name": "Test User",
            "public_gists": 2,
            "public_repos": 3,
            "updated_at": "2023-01-01T00:00:00Z",
        }

        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.github.com/user", status=503)
            rsps.add(
                responses.GET, "https://api.github.com/user", json=user_json, status=200
            )

            gh.me()
            assert len(rsps.calls) == 2

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
            gh = get_github_api_for_repo(None, "https://github.com/TestOwner/TestRepo/")
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
                get_github_api_for_repo(None, "https://github.com/TestOwner/TestRepo/")

    @responses.activate
    @mock.patch("cumulusci.core.github.GitHub")
    def test_get_github_api_for_repo__token(self, GitHub):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token"}):
            gh = get_github_api_for_repo(None, "https://github.com/TestOwner/TestRepo/")
        gh.login.assert_called_once_with(token="token")

    @responses.activate
    @mock.patch("cumulusci.core.github.GitHubEnterprise")
    def test_get_github_api_for_repo__enterprise(
        self, GitHubEnterprise, keychain_enterprise
    ):

        gh = get_github_api_for_repo(
            keychain_enterprise, "https://git.enterprise.domain.com/TestOwner/TestRepo/"
        )

        gh.login.assert_called_once_with(token="ATOKEN")

    @responses.activate
    def test_validate_service(self, keychain_enterprise):
        responses.add("GET", "https://api.github.com/user", status=401, headers={})

        with pytest.raises(GithubException):
            validate_service(
                {"username": "BOGUS", "token": "BOGUS"}, keychain_enterprise
            )

    @responses.activate
    def test_validate_gh_enterprise(self, keychain_enterprise):
        keychain_enterprise.set_service(
            "github_enterprise",
            "ent2",
            ServiceConfig(
                {
                    "username": "testusername2",
                    "email": "test2@domain.com",
                    "token": "ATOKEN2",
                    "server_domain": "git.enterprise.domain.com",
                }
            ),
        )

        with pytest.raises(
            GithubException,
            match="More than one Github Enterprise service configured for domain git.enterprise.domain.com",
        ):
            validate_gh_enterprise("git.enterprise.domain.com", keychain_enterprise)

    @responses.activate
    def test_get_auth_from_service(self, keychain_enterprise):
        # github service, should be ignored
        keychain_enterprise.set_service(
            "github",
            "ent",
            ServiceConfig(
                {
                    "username": "testusername",
                    "email": "test@domain.com",
                    "token": "ATOKEN",
                }
            ),
        )
        assert (
            get_auth_from_service("git.enterprise.domain.com", keychain_enterprise)
            == "ATOKEN"
        )

        with pytest.raises(
            ServiceNotConfigured,
            match="No Github Enterprise service configured for domain garbage",
        ):
            get_auth_from_service("garbage", keychain_enterprise)

    @pytest.mark.parametrize(
        "domain,client",
        [
            (None, GitHub),
            ("github.com", GitHub),
            ("api.github.com", GitHub),
            ("git.enterprise.domain.com", GitHubEnterprise),
        ],
    )
    def test_determine_github_client(self, domain, client):
        client_result = _determine_github_client(domain, {})
        assert type(client_result) is client

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

        pull_requests = get_pull_requests_by_head(repo, "main")
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
        mock_util.mock_pulls(base="main", head="TestOwner:some-branch")
        pull_requests = get_pull_requests_with_base_branch(
            repo, "main", head="some-branch"
        )
        assert 0 == len(pull_requests)

        responses.reset()
        mock_util.mock_pulls(pulls=self._get_expected_pull_requests(3), base="main")
        pull_requests = get_pull_requests_with_base_branch(repo, "main")
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
            url="https://api.github.com/gists",
            json=self._get_expected_gist(description, files),
            status=201,
        )

    @responses.activate
    def test_create_gist_no_scope(self, gh_api):
        responses.add(
            method=responses.POST,
            url="https://api.github.com/gists",
            status=403,
        )

        self.init_github()

        description = "Test Gist Creation"
        filename = "error_output.txt"
        content = "Hello there gist!"
        files = {filename: content}

        with pytest.raises(GithubApiError, match="scopes: gist"):
            create_gist(gh_api, description, files)

    @responses.activate
    def test_get_tag_by_name(self, repo):
        self.init_github()
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/tag_SHA",
            json=self._get_expected_tag_ref("tag_SHA", "tag_SHA"),
            status=200,
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/tags/tag_SHA",
            json=self._get_expected_tag("beta/1.0", "tag_SHA"),
            status=200,
        )
        tag = get_tag_by_name(repo, "tag_SHA")
        assert tag.tag == "beta/1.0"

    @responses.activate
    def test_get_tag_by_name__404(self, repo):
        self.init_github()
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/tag_SHA",
            json=self._get_expected_tag_ref("tag_SHA", "tag_SHA"),
            status=200,
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/tags/tag_SHA",
            json=self._get_expected_tag("beta/1.0", "tag_SHA"),
            status=404,
        )
        with pytest.raises(GithubApiNotFoundError):
            get_tag_by_name(repo, "tag_SHA")

    @responses.activate
    def test_current_tag_is_lightweight(self, repo):
        self.init_github()
        light_tag = self._get_expected_tag_ref("tag_SHA", "tag_SHA")
        light_tag["object"]["type"] = "commit"
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/tag_SHA",
            json=light_tag,
            status=200,
        )
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/tags/tag_SHA",
            json=self._get_expected_tag("beta/1.0", "tag_SHA"),
            status=404,
        )
        with pytest.raises(GithubApiNotFoundError) as exc:
            get_tag_by_name(repo, "tag_SHA")

        assert "not an annotated tag" in str(exc)

    @responses.activate
    def test_get_ref_by_name(self, repo):
        self.init_github()
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/tag_SHA",
            json=self._get_expected_tag_ref("tag_SHA", "tag_SHA"),
            status=200,
        )
        ref = get_ref_for_tag(repo, "tag_SHA")
        assert ref.object.sha == "tag_SHA"

    @responses.activate
    def test_get_ref_by_name__404(self, repo):
        self.init_github()
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/tag_SHA",
            json=self._get_expected_tag_ref("tag_SHA", "tag_SHA"),
            status=404,
        )
        with pytest.raises(GithubApiNotFoundError):
            get_ref_for_tag(repo, "tag_SHA")

    @responses.activate
    def test_get_version_id_from_tag(self, repo):
        self.init_github()
        responses.add(  # the ref for the tag is fetched first
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/test-tag-name",
            json=self._get_expected_tag_ref("test-tag-name", "tag_SHA"),
            status=200,
        )
        tag_message = """Release of Test Package\nversion_id: 04t000000000000\n\ndependencies: []"""
        responses.add(  # then we fetch that actual tag with the ref
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/tags/tag_SHA",
            json=self._get_expected_tag("beta/1.0", "tag_SHA", message=tag_message),
            status=200,
        )
        version_id = get_version_id_from_tag(repo, "test-tag-name")
        assert version_id == "04t000000000000"

    @responses.activate
    def test_get_version_id_from_tag__dependency_error(self, repo):
        self.init_github()
        responses.add(  # the ref for the tag is fetched first
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/ref/tags/test-tag-name",
            json=self._get_expected_tag_ref("test-tag-name", "tag_SHA"),
            status=200,
        )
        tag_message = (
            """Release of Test Package\nversion_id: invalid_id\n\ndependencies: []"""
        )
        responses.add(  # then we fetch that actual tag with the ref
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/git/tags/tag_SHA",
            json=self._get_expected_tag("beta/1.0", "tag_SHA", message=tag_message),
            status=200,
        )
        with pytest.raises(DependencyLookupError):
            get_version_id_from_tag(repo, "test-tag-name")

    @responses.activate
    def test_get_commit(self, repo):
        self.init_github()
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/commits/DUMMY_SHA",
            json=self._get_expected_commit("DUMMY_SHA"),
            status=200,
        )
        commit = get_commit(repo, "DUMMY_SHA")
        assert commit.sha == "DUMMY_SHA"

    @responses.activate
    def test_get_commit__dependency_error(self, repo):
        self.init_github()
        responses.add(
            method=responses.GET,
            url=self.repo_api_url + "/commits/DUMMY_SHA",
            json={"message": "Could not verify object"},
            status=422,
        )
        with pytest.raises(
            DependencyLookupError, match="Could not find commit DUMMY_SHA on GitHub"
        ):
            get_commit(repo, "DUMMY_SHA")

    def test_get_oauth_scopes(self):
        resp = Response()
        resp.headers["X-OAuth-Scopes"] = "repo, user"
        assert {"repo", "user"} == get_oauth_scopes(resp)

        resp = Response()
        resp.headers["X-OAuth-Scopes"] = "repo"
        assert {"repo"} == get_oauth_scopes(resp)

        resp = Response()
        assert set() == get_oauth_scopes(resp)

    def test_get_sso_disabled_orgs(self):
        resp = Response()
        assert [] == get_sso_disabled_orgs(resp)

        resp = Response()
        resp.headers["X-Github-Sso"] = "partial-results; organizations=0810298,20348880"
        assert ["0810298", "20348880"] == get_sso_disabled_orgs(resp)

    def test_check_github_sso_no_forbidden(self):
        resp = Response()
        resp.status_code = 401
        exc = AuthenticationFailed(resp)
        assert check_github_sso_auth(exc) == ""

        resp.status_code = 403
        exc = ForbiddenError(resp)
        assert check_github_sso_auth(exc) == ""

    @mock.patch("webbrowser.open")
    def test_check_github_sso_unauthorized_token(self, browser_open):
        resp = Response()
        resp.status_code = 403
        auth_url = "https://github.com/orgs/foo/sso?authorization_request=longhash"
        resp.headers["X-Github-Sso"] = f"required; url={auth_url}"
        exc = ForbiddenError(resp)

        check_github_sso_auth(exc)

        browser_open.assert_called_with(auth_url)

    def test_check_github_sso_partial_auth(self):
        resp = Response()
        resp.status_code = 403
        resp.headers["X-Github-Sso"] = "partial-results; organizations=0810298,20348880"
        exc = ForbiddenError(resp)

        expected_err_msg = f"{SSO_WARNING} ['0810298', '20348880']"
        actual_error_msg = check_github_sso_auth(exc).strip()
        assert expected_err_msg == actual_error_msg

    def test_github_oauth_org_restricted(self):
        resp = Response()
        resp.status_code = 403
        body = {"message": "organization has enabled OAuth App access restriction"}
        resp._content = json.dumps(body)
        exc = ForbiddenError(resp)

        expected_warning = "You may also use a Personal Access Token as a workaround."
        actual_error_msg = warn_oauth_restricted(exc)
        assert expected_warning in actual_error_msg

    def test_format_gh3_exc_retry(self):
        resp = Response()
        resp.status_code = 401
        message = "Max retries exceeded with url: foo (Caused by ResponseError('too many 401 error responses',))"
        base_exc = RetryError(message, response=resp)
        exc = TransportError(base_exc)
        assert UNAUTHORIZED_WARNING == format_github3_exception(exc)

    def test_format_gh3_self_signed_ssl(self):
        resp = Response()
        resp.status_code = 401
        message = "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate in certificate chain"
        base_exc = SSLError(message, response=resp)
        exc = ConnectionError(base_exc)
        assert SELF_SIGNED_WARNING == format_github3_exception(exc)

        # Test passsthrough of other conenction errors
        base_exc = SSLError(response=resp)
        exc = ConnectionError(base_exc)
        assert format_github3_exception(exc) == ""

    def test_format_url_from_exc(self):
        resp = Response()
        resp.status_code = 401
        resp.url = expected_url = "http://example.com"
        message = "Max retries exceeded with url: foo (Caused by ResponseError('too many 401 error responses',))"
        base_exc = RetryError(message, response=resp)
        exc = TransportError(base_exc)
        resp_exc = ResponseError(resp)
        assert expected_url == request_url_from_exc(exc)
        assert expected_url == request_url_from_exc(resp_exc)

    def test_catch_common_decorator(self):
        resp = Response()
        resp.status_code = 403
        resp.headers["X-Github-Sso"] = "partial-results; organizations=0810298,20348880"
        resp.url = "http://zombo.com"

        expected_err_msg = "http://zombo.com\nResults may be incomplete. You have not granted your Personal Access token access to the following organizations: ['0810298', '20348880']"

        @catch_common_github_auth_errors
        def test_func():
            raise ForbiddenError(resp)

        with pytest.raises(GithubApiError) as exc:
            test_func()
            actual_error_msg = exc.message
            assert expected_err_msg == actual_error_msg

    @responses.activate
    def test_catch_common_decorator_transport_url(self):
        mock_rsp = responses.Response(
            method=responses.GET,
            url="https://api.github.com/rate_limit",
            status=401,
            headers={"X-Github-Sso": "partial-results; organizations=0810298,20348880"},
        )
        responses.add(mock_rsp)

        rsp = requests.get("https://api.github.com/rate_limit")
        responses.calls.reset()

        retry_err = RetryError("too many 401 error responses")
        retry_err.response = rsp
        mock_rsp.body = retry_err

        @catch_common_github_auth_errors
        def test_func():
            GitHub().rate_limit()

        with pytest.raises(
            GithubApiError, match="^https://api.github.com/rate_limit\n"
        ):
            test_func()

    def test_catch_common_decorator_ignores(self):
        resp = Response()
        resp.status_code = 401

        @catch_common_github_auth_errors
        def test_func():
            e = RequestException(response=resp)
            raise TransportError(e)

        with pytest.raises(TransportError):
            test_func()

    @responses.activate
    def test_catch_common_decorator_connection_error(self):

        mock_rsp = responses.Response(
            method=responses.GET,
            url="https://api.github.com/rate_limit",
            body=ConnectionError("self signed certificate"),
        )
        responses.add(mock_rsp)

        @catch_common_github_auth_errors
        def test_func():
            GitHub().rate_limit()

        with pytest.raises(
            GithubApiError,
            match="(self-signed certificate in the certificate chain)",
        ):
            test_func()

    @responses.activate
    def test_validate_no_repo_exc(self, keychain_enterprise):
        service_dict = {
            "username": "e2ac67",
            "token": "ghp_cf83e1357eefb8bdf1542850d66d8007d620e4",
            "email": "testerson@test.com",
        }
        responses.add(
            responses.GET,
            "https://api.github.com/user",
            json={
                "login": "e2ac67",
                "id": 91303375,
                "node_id": "MDQ6VXNlcjkxMzAzMzc1",
                "avatar_url": "https://avatars.githubusercontent.com/u/91303375?v=4",
                "gravatar_id": "",
                "url": "https://api.github.com/users/e2ac67",
                "html_url": "https://github.com/e2ac67",
                "followers_url": "https://api.github.com/users/e2ac67/followers",
                "following_url": "https://api.github.com/users/e2ac67/following{/other_user}",
                "gists_url": "https://api.github.com/users/e2ac67/gists{/gist_id}",
                "starred_url": "https://api.github.com/users/e2ac67/starred{/owner}{/repo}",
                "subscriptions_url": "https://api.github.com/users/e2ac67/subscriptions",
                "organizations_url": "https://api.github.com/users/e2ac67/orgs",
                "repos_url": "https://api.github.com/users/e2ac67/repos",
                "events_url": "https://api.github.com/users/e2ac67/events{/privacy}",
                "received_events_url": "https://api.github.com/users/e2ac67/received_events",
                "type": "User",
                "site_admin": False,
                "name": None,
                "company": None,
                "blog": "",
                "location": None,
                "email": None,
                "hireable": None,
                "bio": None,
                "twitter_username": None,
                "public_repos": 0,
                "public_gists": 0,
                "followers": 0,
                "following": 0,
                "created_at": "2021-09-24T03:53:02Z",
                "updated_at": "2021-09-24T03:59:40Z",
            },
        )
        responses.add(
            responses.GET,
            "https://api.github.com/user/orgs",
            json=[],
        )
        responses.add(
            responses.GET,
            "https://api.github.com/user/repos",
            json=[],
            headers={
                "GitHub-Authentication-Token-Expiration": "2021-10-07 19:07:53 UTC",
                "X-OAuth-Scopes": "gist, repo",
            },
        )
        updated_dict = validate_service(service_dict, keychain_enterprise)
        expected_dict = {
            "username": "e2ac67",
            "token": "ghp_cf83e1357eefb8bdf1542850d66d8007d620e4",
            "email": "testerson@test.com",
            "Organizations": "",
            "scopes": "gist, repo",
            "expires": "2021-10-07 19:07:53 UTC",
        }
        assert expected_dict == updated_dict

    @responses.activate
    def test_validate_bad_auth(self, keychain_enterprise):
        service_dict = {
            "username": "e2ac67",
            "token": "bad_cf83e1357eefb8bdf1542850d66d8007d620e4",
            "email": "testerson@test.com",
        }

        responses.add(
            responses.GET,
            "https://api.github.com/user",
            json={
                "message": "Bad credentials",
                "documentation_url": "https://docs.github.com/rest",
            },
            status=401,
        )

        with pytest.raises(cumulusci.core.exceptions.GithubException) as e:
            validate_service(service_dict, keychain_enterprise)
        assert "401" in str(e.value)

    @mock.patch("webbrowser.open")
    @mock.patch("cumulusci.core.github.get_device_code")
    @mock.patch("cumulusci.core.github.get_device_oauth_token", autospec=True)
    def test_get_oauth_device_flow_token(
        self,
        get_token,
        get_code,
        browser_open,
    ):
        device_config = {
            "device_code": "36482450e39b7f27d9a145a96898d29365a4e73f",
            "user_code": "3E15-9D06",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 899,
            "interval": 5,
        }
        get_code.return_value = device_config
        get_token.return_value = {
            "access_token": "expected_access_token",
            "token_type": "bearer",
            "scope": "gist,repo",
        }

        returned_token = get_oauth_device_flow_token()

        assert returned_token == "expected_access_token"
        get_token.assert_called_once()
        get_code.assert_called_once()
        browser_open.assert_called_with("https://github.com/login/device")

    @responses.activate
    @pytest.mark.parametrize(
        ("base_url", "endpoint"),
        (
            ("https://api.github.com", "https://api.github.com/graphql"),
            (
                "https://github.enterprise.server/api/v3",
                "https://github.enterprise.server/api/graphql",
            ),
        ),
    )
    def test_get_latest_prerelease(self, base_url, endpoint):
        expected_tag = "beta/1.0-Beta_1"
        query_result = self._get_expected_prerelease_tag_gql(expected_tag)

        responses.add(
            "POST",
            endpoint,
            json=query_result,
        )

        repo: Repository = mock.MagicMock()
        repo.session = mock.MagicMock()
        repo.session.base_url = base_url
        repo.session.request = requests.request

        get_latest_prerelease(repo=repo)
        assert responses.assert_call_count(endpoint, 1)
        repo.release_from_tag.assert_called_once_with(expected_tag)
