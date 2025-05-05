# import functools
# import io
import os

# import re
# import time
import webbrowser

# from string import Template
# from typing import Callable, Optional, Union
from typing import Optional, Union
from urllib.parse import urlparse

import github3
from github3 import GitHub, GitHubEnterprise  # , login
from github3.exceptions import (
    AuthenticationFailed,
    ConnectionError,
    ResponseError,
    TransportError,
)

# from github3.git import Reference, Tag
# from github3.pulls import ShortPullRequest
# from github3.repos.commit import RepoCommit
# from github3.repos.release import Release
# from github3.repos.repo import Repository
from github3.session import GitHubSession
from requests.adapters import HTTPAdapter
from requests.exceptions import RetryError
from requests.models import Response
from requests.packages.urllib3.util.retry import Retry

from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import (  # DependencyLookupError,; GithubApiError,; GithubApiNotFoundError,
    GithubException,
    ServiceNotConfigured,
)
from cumulusci.core.keychain import BaseProjectKeychain

# from cumulusci.oauth.client import (
#     OAuth2ClientConfig,
#     OAuth2DeviceConfig,
#     get_device_code,
#     get_device_oauth_token,
# )
from cumulusci.utils.git import parse_repo_url
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.github import GitHubRepository

# from rich.console import Console


# from cumulusci.utils.http.requests_utils import safe_json_from_response
# from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load


OAUTH_DEVICE_APP = {
    "client_id": "2a4bc3e5ce4f2c49a957",
    "auth_uri": "https://github.com/login/device/code",
    "token_uri": "https://github.com/login/oauth/access_token",
    "scope": "repo gist",
}
SSO_WARNING = """Results may be incomplete. You have not granted your Personal Access token access to the following organizations:"""
UNAUTHORIZED_WARNING = """
Bad credentials. Verify that your personal access token is correct and that you are authorized to access this resource.
"""
SELF_SIGNED_WARNING = """
There was a problem verifying the SSL Certificate due to a certificate authority that isn't trusted or a self-signed certificate in the certificate chain. Try setting CUMULUSCI_SYSTEM_CERTS Environment Variable to 'True'. See https://cumulusci.readthedocs.io/en/stable/env-var-reference.html?#cumulusci-system-certs
"""


class GitHubRety(Retry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def increment(self, *args, **kwargs):
        # Check for connnection and fail on SSLerror
        # SSLCertVerificationError
        if "error" in kwargs:
            error = kwargs["error"]
            error_str = "CERTIFICATE_VERIFY_FAILED"
            if error_str in str(error):
                raise error
        # finally call increment
        return super().increment(*args, **kwargs)


# Prepare request retry policy to be attached to github sessions.
# 401 is a weird status code to retry, but sometimes it happens spuriously
# and https://github.community/t5/GitHub-API-Development-and/Random-401-errors-after-using-freshly-generated-installation/m-p/22905 suggests retrying
retries = GitHubRety(status_forcelist=(401, 502, 503, 504), backoff_factor=0.3)
adapter = HTTPAdapter(max_retries=retries)

INSTALLATIONS = {}


def _determine_github_client(host: Union[str, None], client_params: dict) -> GitHub:
    """Determine the appropriate GitHub client based on the host.

    Args:
        host (Union[str, None]): The host for the GitHub client.
        client_params (dict): Parameters for the GitHub client.

    Returns:
        GitHub: The GitHub client instance.
    """
    # also covers "api.github.com"
    is_github: bool = host in (None, "None") or "github.com" in host
    client_cls: GitHub = GitHub if is_github else GitHubEnterprise  # type: ignore
    params: dict = client_params
    if not is_github:
        params["url"] = "https://" + host  # type: ignore

    return client_cls(**params)


def get_github_api_for_repo(keychain, repo_url, session=None) -> GitHub:
    owner, repo_name, host = parse_repo_url(repo_url)
    gh: GitHub = _determine_github_client(
        host,
        {
            "session": session
            or GitHubSession(default_read_timeout=30, default_connect_timeout=30)
        },
    )

    # Apply retry policy
    gh.session.mount("http://", adapter)
    gh.session.mount("https://", adapter)

    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    APP_KEY = os.environ.get("GITHUB_APP_KEY", "").encode("utf-8")
    APP_ID = os.environ.get("GITHUB_APP_ID")
    if APP_ID and APP_KEY:
        installation = INSTALLATIONS.get((owner, repo_name))
        if installation is None:
            gh.login_as_app(APP_KEY, APP_ID, expire_in=120)
            try:
                installation = gh.app_installation_for_repository(owner, repo_name)
            except github3.exceptions.NotFoundError:
                raise GithubException(
                    f"Could not access {owner}/{repo_name} using GitHub app. "
                    "Does the app need to be installed for this repository?"
                )
            INSTALLATIONS[(owner, repo_name)] = installation
        gh.login_as_app_installation(APP_KEY, APP_ID, installation.id)
    elif GITHUB_TOKEN:
        gh.login(token=GITHUB_TOKEN)
    else:
        token = get_auth_from_service(host, keychain)
        gh.login(token=token)

    return gh


def get_auth_from_service(host, keychain) -> str:
    """
    Given a host extracted from a repo_url, returns the username and token for
    the first service with a matching server_domain
    """
    if host is None or host == "None" or "github.com" in host:
        service_config = keychain.get_service("github")
    else:
        services = keychain.get_services_for_type("github_enterprise")
        service_by_host = {service.server_domain: service for service in services}

        # Check when connecting to server, but not when creating new service as this would always catch
        if list(service_by_host.keys()).count(host) == 0:
            raise ServiceNotConfigured(
                f"No Github Enterprise service configured for domain {host}."
            )

        service_config = service_by_host[host]

    # Basic Auth no longer supported on github.com, so only returning token
    # this requires GitHub Enterprise to use token auth and not Basic auth
    # docs.github.com/en/rest/overview/other-authentication-methods#via-username-and-password
    return service_config.token


def validate_gh_enterprise(host: str, keychain) -> None:
    services = keychain.get_services_for_type("github_enterprise")
    if services:
        hosts = [service.server_domain for service in services]
        if hosts.count(host) > 1:
            raise GithubException(
                f"More than one Github Enterprise service configured for domain {host}."
            )


def get_sso_disabled_orgs(response: Response) -> list:
    """
    Given a response from Github, return a list of organization IDs without SSO
    grants.
    """
    disabled_orgs = []
    sso_header = response.headers.get("X-Github-Sso")
    partial_results_prefix = "partial-results; organizations="

    if sso_header and partial_results_prefix in sso_header:
        disabled_orgs = sso_header[len(partial_results_prefix) :].split(",")

    return disabled_orgs


def format_github3_exception(
    exc: Union[ResponseError, TransportError, ConnectionError]
) -> str:
    """Checks github3 exceptions for the most common GitHub authentication
    issues, returning a user-friendly message if found.

    @param exc: The exception to process
    @returns: The formatted exception string
    """
    user_warning = ""

    too_many_str = "too many 401 error responses"
    is_bad_auth_retry = (
        type(exc) is TransportError
        and type(exc.exception) is RetryError
        and too_many_str in str(exc.exception)
    )
    is_auth_failure = type(exc) is AuthenticationFailed

    if is_bad_auth_retry or is_auth_failure:
        user_warning = UNAUTHORIZED_WARNING

    if isinstance(exc, ResponseError):
        scope_error_msg = check_github_scopes(exc)
        sso_error_msg = check_github_sso_auth(exc)
        user_warning = scope_error_msg + sso_error_msg

    if isinstance(exc, ConnectionError):
        if "self signed certificate" in str(exc.exception):
            user_warning = SELF_SIGNED_WARNING
        else:
            return ""

    return user_warning


def get_oauth_scopes(response: Response) -> set:
    """
    Given a response from Github, return the set of OAuth scopes for its
    request.
    """
    authorized_scopes = set()

    # If the token isn't authorized "X-OAuth-Scopes" header won't be present
    x_oauth_scopes = response.headers.get("X-OAuth-Scopes")
    if x_oauth_scopes:
        authorized_scopes = set(x_oauth_scopes.split(", "))

    return authorized_scopes


def check_github_scopes(exc: ResponseError) -> str:
    """
    Parse github3 ResponseError headers for the correct scopes and return a
    warning if the user is missing.

    @param exc: The exception to process
    @returns: The formatted exception string
    """

    user_warning = ""

    has_wrong_status_code = exc.response.status_code not in (403, 404)
    if has_wrong_status_code:
        return user_warning

    token_scopes = get_oauth_scopes(exc.response)

    # Gist resource won't return X-Accepted-OAuth-Scopes for some reason, so this
    # string might be `None`; we discard the empty string if so.
    accepted_scopes = exc.response.headers.get("X-Accepted-OAuth-Scopes") or ""
    accepted_scopes = set(accepted_scopes.split(", "))
    accepted_scopes.discard("")

    request_url = urlparse(exc.response.url)
    if not accepted_scopes and request_url.path == "/gists":
        accepted_scopes = {"gist"}

    missing_scopes = accepted_scopes.difference(token_scopes)
    if missing_scopes:
        user_warning = f"Your token may be missing the following scopes: {', '.join(missing_scopes)}\n"
        # This assumes we're not on enterprise and 'api.github.com' == request_url.hostname
        user_warning += (
            "Visit Settings > Developer settings > Personal access tokens to add them."
        )

    return user_warning


def check_github_sso_auth(exc: ResponseError) -> str:
    """
    Check ResponseError header for SSO authorization and return a warning if
    required

    @param exc: The exception to process
    @returns: The formatted exception string
    """
    user_warning = ""
    headers = exc.response.headers

    if exc.response.status_code != 403 or "X-Github-Sso" not in headers:
        return user_warning

    sso_header = str(headers["X-Github-Sso"] or "")
    if sso_header.startswith("required; url="):
        # In this case the message from github is good enough, but we can help
        # the user by opening a browser to authorize the token.
        auth_url = sso_header.split("url=", maxsplit=1)[1]
        user_warning = f"{exc.message}\n{auth_url}"
        webbrowser.open(auth_url)
    elif sso_header.startswith("partial-results"):
        # In cases where we don't have complete results we get the
        # partal-results header, so return the organization IDs. This may or
        # may not be useful without help from us to lookup the org IDs.
        unauthorized_org_ids = get_sso_disabled_orgs(exc.response)
        user_warning = f"{SSO_WARNING} {unauthorized_org_ids}"

    return user_warning


class GitHubService(VCSService):
    service_type = "github"
    _repo: GitHubRepository
    github: GitHub

    def __init__(self, config: BaseProjectConfig, name: Optional[str] = None, **kwargs):
        """Initializes the GitHub service with the given project configuration.
        Args:
            config (BaseProjectConfig): The configuration for the GitHub service.
            name (str): The name or alias of the VCS service.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(config, **kwargs)

        self.github = get_github_api_for_repo(self.keychain, self.config.repo_url)
        self._repo: GitHubRepository = None

    @property
    def repo(self) -> GitHubRepository:
        """Returns the GitHub repository associated with the service."""
        return self._repo

    @repo.setter
    def repo(self, repo: GitHubRepository):
        """Set the GitHub repository associated with the service.

        Args:
            repo (GitHubRepository): The GitHub repository instance to set.
        """
        self._repo = repo

    @classmethod
    def validate_service(cls, options: dict, keychain) -> dict:
        """Validates service for Github and GithubEnterprise.

        Args:
            options (dict): The options for the service validation.
            keychain: The keychain for accessing project credentials.

        Returns:
            dict: The validated options for the service.
        """
        username = options["username"]
        token = options["token"]
        # Github service doesn't have "server_domain",
        server_domain = options.get("server_domain", None)

        gh = _determine_github_client(server_domain, {"token": token})
        if isinstance(gh, GitHubEnterprise):
            validate_gh_enterprise(server_domain, keychain)
        try:
            authed_user = gh.me()
            auth_login = authed_user.login
            assert username == auth_login, f"{username}, {auth_login}"
        except AssertionError as e:
            raise GithubException(
                f"Service username and token username do not match. ({str(e)})"
            )
        except Exception as e:
            warning_msg = format_github3_exception(e) or str(e)
            raise GithubException(
                f"Could not confirm access to the GitHub API: {warning_msg}"
            )
        else:
            member_orgs = {f"{org.id}": f"{org.login}" for org in gh.organizations()}
            options["Organizations"] = ", ".join([k for k in member_orgs.values()])

            # We're checking for a partial-response SSO header and /user/orgs
            # doesn't include one, so we need /user/repos instead.
            repo_generator = gh.repositories()
            _ = next(repo_generator, None)
            repo_response = repo_generator.last_response
            options["scopes"] = ", ".join(sorted(get_oauth_scopes(repo_response)))

            unauthorized_org_ids = get_sso_disabled_orgs(repo_response)
            unauthorized_orgs = {
                k: member_orgs[k] for k in unauthorized_org_ids if k in member_orgs
            }
            if unauthorized_orgs:
                options["SSO Disabled"] = ", ".join(
                    [k for k in unauthorized_orgs.values()]
                )

            expiration_date = repo_response.headers.get(
                "GitHub-Authentication-Token-Expiration"
            )
            if expiration_date:
                options["expires"] = expiration_date

        return options

    def get_repository(self) -> GitHubRepository:
        """Returns the GitHub repository."""
        if self._repo is None:
            self._repo = GitHubRepository(
                self.github,
                self.config,
                logger=self.logger,
                service_type=self.service_type,
                service_config=self.service_config,
            )
        return self.repo


class GitHubEnterpriseService(GitHubService):
    service_type = "github_enterprise"
    _repo: GitHubRepository

    def __init__(self, config: dict, name: str, keychain: BaseProjectKeychain):
        super().__init__(config, name, keychain)
