# import json
import os
from datetime import datetime

# from ssl import SSLCertVerificationError
from unittest import mock

import pytest

# import requests
import responses
from github3 import GitHub, GitHubEnterprise
from github3.exceptions import (  # ResponseError,
    AuthenticationFailed,
    ConnectionError,
    ForbiddenError,
    TransportError,
)

# from github3.pulls import ShortPullRequest
from github3.repos.repo import Repository
from github3.session import AppInstallationTokenAuth
from requests.exceptions import RetryError, SSLError  # RequestException,
from requests.models import Response

# import cumulusci
import cumulusci.vcs.github.service as github
from cumulusci.core.config import BaseProjectConfig, ServiceConfig, UniversalConfig
from cumulusci.core.exceptions import (  # DependencyLookupError,; GithubApiError,; GithubApiNotFoundError,
    GithubException,
    ServiceNotConfigured,
)
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tasks.release_notes.tests.utils import MockUtil
from cumulusci.vcs.github.service import (  # GitHubService, add_labels_to_pull_request,; catch_common_github_auth_errors,; create_gist,; create_pull_request,; get_commit,; get_github_api,; get_latest_prerelease,; get_oauth_device_flow_token,; get_pull_requests_by_commit,; get_pull_requests_by_head,; get_pull_requests_with_base_branch,; get_ref_for_tag,; get_tag_by_name,; get_version_id_from_tag,; is_label_on_pull_request,; is_pull_request_merged,; markdown_link_to_pr,; request_url_from_exc,; validate_service,; warn_oauth_restricted,
    SELF_SIGNED_WARNING,
    SSO_WARNING,
    UNAUTHORIZED_WARNING,
    GitHubEnterpriseService,
    _determine_github_client,
    check_github_scopes,
    check_github_sso_auth,
    format_github3_exception,
    get_auth_from_service,
    get_github_api_for_repo,
    get_oauth_scopes,
    get_sso_disabled_orgs,
    validate_gh_enterprise,
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
    @mock.patch("cumulusci.vcs.github.service.GitHub")
    def test_get_github_api_for_repo__token(self, GitHub):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token"}):
            gh = get_github_api_for_repo(None, "https://github.com/TestOwner/TestRepo/")
        gh.login.assert_called_once_with(token="token")

    @responses.activate
    @mock.patch("cumulusci.vcs.github.service.GitHubEnterprise")
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
            GitHubEnterpriseService.validate_service(
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
        assert isinstance(client_result, client)

    def test_get_sso_disabled_orgs(self):
        resp = Response()
        assert [] == get_sso_disabled_orgs(resp)

        resp = Response()
        resp.headers["X-Github-Sso"] = "partial-results; organizations=0810298,20348880"
        assert ["0810298", "20348880"] == get_sso_disabled_orgs(resp)

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

    def test_get_oauth_scopes(self):
        resp = Response()
        resp.headers["X-OAuth-Scopes"] = "repo, user"
        assert {"repo", "user"} == get_oauth_scopes(resp)

        resp = Response()
        resp.headers["X-OAuth-Scopes"] = "repo"
        assert {"repo"} == get_oauth_scopes(resp)

        resp = Response()
        assert set() == get_oauth_scopes(resp)

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


def test_githubrety_init():
    from cumulusci.vcs.github.service import GitHubRety

    retry = GitHubRety(total=1)
    assert isinstance(retry, GitHubRety)


def test_githubrety_increment_calls_super(monkeypatch):
    from requests.packages.urllib3.util import retry as urllib3_retry

    from cumulusci.vcs.github.service import GitHubRety

    called = {}

    def fake_increment(self, *args, **kwargs):
        called["yes"] = True
        return "super-called"

    monkeypatch.setattr(urllib3_retry.Retry, "increment", fake_increment)
    retry = GitHubRety(total=1)
    result = retry.increment()
    assert called["yes"]
    assert result == "super-called"


def test_githubrety_increment_raises_on_cert_error():
    from cumulusci.vcs.github.service import GitHubRety

    retry = GitHubRety(total=1)

    class DummyError(Exception):
        pass

    error = DummyError("CERTIFICATE_VERIFY_FAILED: something bad")
    with pytest.raises(DummyError):
        retry.increment(error=error)


def test_check_github_scopes_wrong_status_code():
    from github3.exceptions import ResponseError

    resp = Response()
    resp.status_code = 401  # Not 403 or 404
    exc = ResponseError(resp)
    assert check_github_scopes(exc) == ""


def test_check_github_scopes_no_missing_scopes():
    from github3.exceptions import ResponseError

    resp = Response()
    resp.status_code = 403
    resp.headers["X-Accepted-OAuth-Scopes"] = "repo, user"
    resp.headers["X-OAuth-Scopes"] = "repo, user"
    resp.url = "https://api.github.com/repos/foo/bar"
    exc = ResponseError(resp)
    assert check_github_scopes(exc) == ""


def test_check_github_scopes_missing_scopes():
    from github3.exceptions import ResponseError

    resp = Response()
    resp.status_code = 403
    resp.headers["X-Accepted-OAuth-Scopes"] = "repo, user"
    resp.headers["X-OAuth-Scopes"] = "repo"
    resp.url = "https://api.github.com/repos/foo/bar"
    exc = ResponseError(resp)
    result = check_github_scopes(exc)
    assert "Your token may be missing the following scopes: user" in result
    assert "Personal access tokens" in result


def test_check_github_scopes_empty_accepted_scopes():
    from github3.exceptions import ResponseError

    resp = Response()
    resp.status_code = 403
    resp.headers["X-Accepted-OAuth-Scopes"] = ""
    resp.headers["X-OAuth-Scopes"] = "repo"
    resp.url = "https://api.github.com/repos/foo/bar"
    exc = ResponseError(resp)
    assert check_github_scopes(exc) == ""


def test_check_github_scopes_gist_special_case_missing_scope():
    from github3.exceptions import ResponseError

    resp = Response()
    resp.status_code = 404
    resp.headers["X-Accepted-OAuth-Scopes"] = ""
    resp.headers["X-OAuth-Scopes"] = ""
    resp.url = "https://api.github.com/gists"
    exc = ResponseError(resp)
    result = check_github_scopes(exc)
    assert "Your token may be missing the following scopes: gist" in result
    assert "Personal access tokens" in result


def test_check_github_scopes_gist_special_case_has_scope():
    from github3.exceptions import ResponseError

    resp = Response()
    resp.status_code = 404
    resp.headers["X-Accepted-OAuth-Scopes"] = ""
    resp.headers["X-OAuth-Scopes"] = "gist"
    resp.url = "https://api.github.com/gists"
    exc = ResponseError(resp)
    assert check_github_scopes(exc) == ""
