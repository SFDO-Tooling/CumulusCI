import functools
import io
import os
import re
import time
import webbrowser
from string import Template
from typing import Callable, Optional, Union
from urllib.parse import urlparse

import github3
from github3 import GitHub, GitHubEnterprise, login
from github3.exceptions import (
    AuthenticationFailed,
    ConnectionError,
    ResponseError,
    TransportError,
)
from github3.git import Reference, Tag
from github3.pulls import ShortPullRequest
from github3.repos.commit import RepoCommit
from github3.repos.release import Release
from github3.repos.repo import Repository
from github3.session import GitHubSession
from requests.adapters import HTTPAdapter
from requests.exceptions import RetryError
from requests.models import Response
from requests.packages.urllib3.util.retry import Retry
from rich.console import Console

from cumulusci.core.exceptions import (
    DependencyLookupError,
    GithubApiError,
    GithubApiNotFoundError,
    GithubException,
    ServiceNotConfigured,
)
from cumulusci.oauth.client import (
    OAuth2ClientConfig,
    OAuth2DeviceConfig,
    get_device_code,
    get_device_oauth_token,
)
from cumulusci.utils.git import parse_repo_url
from cumulusci.utils.http.requests_utils import safe_json_from_response
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load

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


def get_github_api(username=None, password=None):
    """Old API that only handles logging in as a user.

    Here for backwards-compatibility during the transition.
    """
    gh = login(username, password)
    gh.session.mount("http://", adapter)
    gh.session.mount("https://", adapter)
    return gh


INSTALLATIONS = {}


def _determine_github_client(host: str, client_params: dict) -> GitHub:
    # also covers "api.github.com"
    is_github: bool = host in (None, "None") or "github.com" in host
    client_cls: GitHub = GitHub if is_github else GitHubEnterprise  # type: ignore
    params: dict = client_params
    if not is_github:
        params["url"] = "https://" + host  # type: ignore

    return client_cls(**params)


def get_github_api_for_repo(keychain, repo_url, session=None):
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


def get_auth_from_service(host, keychain) -> tuple:
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


def validate_service(options: dict, keychain) -> dict:
    username = options["username"]
    token = options["token"]
    # Github service doesn't have "server_domain",
    server_domain = options.get("server_domain", None)

    gh = _determine_github_client(server_domain, {"token": token})
    if type(gh) == GitHubEnterprise:
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
            options["SSO Disabled"] = ", ".join([k for k in unauthorized_orgs.values()])

        expiration_date = repo_response.headers.get(
            "GitHub-Authentication-Token-Expiration"
        )
        if expiration_date:
            options["expires"] = expiration_date

    return options


def get_pull_requests_with_base_branch(repo, base_branch_name, head=None, state=None):
    """Returns a list of pull requests with the given base branch"""
    if head:
        head = repo.owner.login + ":" + head
    return list(repo.pull_requests(base=base_branch_name, head=head, state=state))


def get_pull_requests_by_head(repo, branch_name):
    """Returns all pull requests with head equal to the given branch name."""
    if branch_name == repo.default_branch:
        return None

    return list(repo.pull_requests(head=repo.owner.login + ":" + branch_name))


def create_pull_request(repo, branch_name, base=None, title=None):
    """Creates a pull request for the given branch"""
    base = base or repo.default_branch
    title = title or "Auto-Generated Pull Request"
    pull_request = repo.create_pull(title, base, branch_name)
    return pull_request


def add_labels_to_pull_request(repo, pull_request, *labels):
    """Adds a label to a pull request via the issue object
    Args:
    * repo: Repository object
    * pull_request: ShortPullRequest object that exists in repo
    * labels: list(str) of labels to add to the pull request"""
    issue = repo.issue(pull_request.number)
    issue.add_labels(*labels)


def is_label_on_pull_request(repo, pull_request, label_name):
    """Returns True if the given label is on the pull request with the given
    pull request number. False otherwise."""
    labels = list(repo.issue(pull_request.number).labels())
    return any(label_name == issue_label.name for issue_label in labels)


def get_pull_requests_by_commit(github, repo, commit_sha):
    endpoint = (
        github.session.base_url
        + f"/repos/{repo.owner.login}/{repo.name}/commits/{commit_sha}/pulls"
    )
    response = github.session.get(
        endpoint, headers={"Accept": "application/vnd.github.groot-preview+json"}
    )
    json_list = safe_json_from_response(response)

    # raises github3.exceptions.IncompleteResposne
    # when these are not present
    for json in json_list:
        json["body_html"] = ""
        json["body_text"] = ""

    return [ShortPullRequest(json, github) for json in json_list]


def is_pull_request_merged(pull_request):
    """Takes a github3.pulls.ShortPullRequest object"""
    return pull_request.merged_at is not None


def markdown_link_to_pr(change_note):
    return f"{change_note.title} [[PR{change_note.number}]({change_note.html_url})]"


def find_latest_release(repo, include_beta=None) -> Optional[Release]:
    try:
        if include_beta:
            return get_latest_prerelease(repo)
        else:
            return repo.latest_release()
    except (github3.exceptions.NotFoundError, StopIteration):
        pass


def get_latest_prerelease(repo: Repository) -> Optional[Release]:
    """Calls GraphQL to retrieve the latest release, ordered chronologically."""
    QUERY = Template(
        """
          query {
            repository(owner: "$owner", name: "$name") {
              releases(last: 1, orderBy: {field: CREATED_AT, direction: ASC}) {
                nodes {
                  tagName
                }
              }
            }
          }
        """
    ).substitute(dict(owner=repo.owner, name=repo.name))

    session: GitHubSession = repo.session
    # HACK: This is a kludgy workaround because GitHub Enterprise Server
    # base_urls in github3.py end in `/api/v3`.
    host = (
        session.base_url[: -len("/v3")]
        if session.base_url.endswith("/v3")
        else session.base_url
    )
    url: str = f"{host}/graphql"
    response: Response = session.request("POST", url, json={"query": QUERY})
    response_dict: dict = response.json()

    if release_tags := response_dict["data"]["repository"]["releases"]["nodes"]:
        return repo.release_from_tag(release_tags[0]["tagName"])


def find_previous_release(repo, prefix=None):
    most_recent = None
    for release in repo.releases():
        if prefix and not release.tag_name.startswith(prefix):
            continue
        if not prefix and release.prerelease:
            continue
        # Return the second release
        if most_recent is None:
            most_recent = release
        else:
            return release


VERSION_ID_RE = re.compile(r"version_id: (\S+)")


def get_version_id_from_commit(repo, commit_sha, context):
    commit = get_commit(repo, commit_sha)

    for status in commit.status().statuses:
        if status.state == "success" and status.context == context:
            match = VERSION_ID_RE.search(status.description)
            if match:
                return match.group(1)


def get_commit(repo: Repository, commit_sha: str) -> Optional[RepoCommit]:
    """Given a SHA1 hash, retrieve a Commit object from the REST API."""
    try:
        commit = repo.commit(commit_sha)
    except (github3.exceptions.NotFoundError, github3.exceptions.UnprocessableEntity):
        # GitHub returns 422 for nonexistent commits in at least some circumstances.
        raise DependencyLookupError(f"Could not find commit {commit_sha} on GitHub")
    return commit


def find_repo_feature_prefix(repo: Repository) -> str:
    contents = repo.file_contents(
        "cumulusci.yml",
        ref=repo.branch(repo.default_branch).commit.sha,
    )
    head_cumulusci_yml = cci_safe_load(io.StringIO(contents.decoded.decode("utf-8")))
    return (
        head_cumulusci_yml.get("project", {})
        .get("git", {})
        .get("prefix_feature", "feature/")
    )


def find_repo_commit_status_context(
    repo: Repository, context_name: str, default: str
) -> str:
    contents = repo.file_contents(
        "cumulusci.yml",
        ref=repo.branch(repo.default_branch).commit.sha,
    )
    head_cumulusci_yml = cci_safe_load(io.StringIO(contents.decoded.decode("utf-8")))
    return (
        head_cumulusci_yml.get("project", {}).get("git", {}).get(context_name, default)
    )


def get_tag_by_name(repo: Repository, tag_name: str) -> Tag:
    """Fetches a tag by name from the given repository"""
    ref: Reference = get_ref_for_tag(repo, tag_name)
    try:
        return repo.tag(ref.object.sha)
    except github3.exceptions.NotFoundError:
        msg = f"Could not find tag '{tag_name}' with SHA {ref.object.sha} on GitHub"
        if ref.object.type != "tag":
            msg += f"\n{tag_name} is not an annotated tag."
        raise GithubApiNotFoundError(msg)


def get_ref_for_tag(repo: Repository, tag_name: str) -> Reference:
    """Gets a Reference object for the tag with the given name"""
    try:
        return repo.ref(f"tags/{tag_name}")
    except github3.exceptions.NotFoundError:
        raise GithubApiNotFoundError(
            f"Could not find reference for 'tags/{tag_name}' on GitHub"
        )


def get_version_id_from_tag(repo: Repository, tag_name: str) -> str:
    """Given the name of a tag, return the version_id in the tag's message.

    @param tag_name: the name of the tag
    @param repo: the repository of the package to look for a release in
    @returns: the 04t id in the tag's messages
    """
    tag = get_tag_by_name(repo, tag_name)
    for line in tag.message.split("\n"):
        if line.startswith("version_id:"):
            version_id = line.split("version_id: ")[1]
            if not version_id.startswith("04t"):
                continue
            return version_id

    raise DependencyLookupError(f"Could not find version_id for tag {tag_name}")


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


def warn_oauth_restricted(exc: ResponseError) -> str:
    user_warning = ""

    is_403 = exc.response.status_code == 403
    org_restricted_oauth_warning = (
        "organization has enabled OAuth App access restriction"
    )

    if is_403 and org_restricted_oauth_warning in str(exc):
        user_warning = str(exc)
        user_warning += "\nYou may also use a Personal Access Token as a workaround."

    return user_warning


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


def catch_common_github_auth_errors(func: Callable) -> Callable:
    """
    A decorator catching the most common Github authentication errors.
    """

    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ConnectionError) as exc:
            if error_msg := format_github3_exception(exc):
                raise GithubApiError(error_msg) from exc
            else:
                raise
        except (ResponseError, TransportError) as exc:
            if error_msg := format_github3_exception(exc):
                url = request_url_from_exc(exc)
                error_msg = f"{url}\n{error_msg}".strip()
                raise GithubApiError(error_msg) from exc
            else:
                raise

    return inner


def request_url_from_exc(exc: Union[ResponseError, TransportError]) -> str:
    if isinstance(exc, TransportError):
        return exc.exception.response.url
    else:
        return exc.response.url


def get_oauth_device_flow_token():
    """Interactive github authorization"""
    config = OAuth2ClientConfig(**OAUTH_DEVICE_APP)
    device_code = OAuth2DeviceConfig(**get_device_code(config))

    console = Console()
    console.print(
        f"[bold] Enter this one-time code: [red]{device_code.user_code}[/red][/bold]"
    )

    console.print(f"Opening {device_code.verification_uri} in your default browser...")
    webbrowser.open(device_code.verification_uri)
    time.sleep(2)  # Give the user a second or two before we start polling

    with console.status("Polling server for authorization..."):
        device_token: dict = get_device_oauth_token(
            client_config=config, device_config=device_code
        )

    access_token = device_token.get("access_token")
    if access_token:
        console.print(
            f"[bold green]Successfully authorized OAuth token ({access_token[:7]}...)[/bold green]"
        )

    return access_token


@catch_common_github_auth_errors
def create_gist(github, description, files):
    """Creates a gist with the given description and files.

    github - an
    description - str
    files - A dict of files in the form of {filename:{'content': content},...}
    """
    return github.create_gist(description, files, public=False)
