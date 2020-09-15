"""Wraps the github3 library to configure request retries."""

import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import github3
from github3 import GitHub
from github3 import login
from github3.pulls import ShortPullRequest
from github3.session import GitHubSession

from cumulusci.core.exceptions import GithubException


# Prepare request retry policy to be attached to github sessions.
# 401 is a weird status code to retry, but sometimes it happens spuriously
# and https://github.community/t5/GitHub-API-Development-and/Random-401-errors-after-using-freshly-generated-installation/m-p/22905 suggests retrying
retries = Retry(status_forcelist=(401, 502, 503, 504), backoff_factor=0.3)
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


def get_github_api_for_repo(keychain, owner, repo, session=None):
    gh = GitHub(
        session=session
        or GitHubSession(default_read_timeout=30, default_connect_timeout=30)
    )
    # Apply retry policy
    gh.session.mount("http://", adapter)
    gh.session.mount("https://", adapter)

    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    APP_KEY = os.environ.get("GITHUB_APP_KEY", "").encode("utf-8")
    APP_ID = os.environ.get("GITHUB_APP_ID")
    if APP_ID and APP_KEY:
        installation = INSTALLATIONS.get((owner, repo))
        if installation is None:
            gh.login_as_app(APP_KEY, APP_ID, expire_in=120)
            try:
                installation = gh.app_installation_for_repository(owner, repo)
            except github3.exceptions.NotFoundError:
                raise GithubException(
                    f"Could not access {owner}/{repo} using GitHub app. "
                    "Does the app need to be installed for this repository?"
                )
            INSTALLATIONS[(owner, repo)] = installation
        gh.login_as_app_installation(APP_KEY, APP_ID, installation.id)
    elif GITHUB_TOKEN:
        gh.login(token=GITHUB_TOKEN)
    else:
        github_config = keychain.get_service("github")
        gh.login(github_config.username, github_config.password)
    return gh


def validate_service(options):
    username = options["username"]
    password = options["password"]
    gh = get_github_api(username, password)
    try:
        gh.rate_limit()
    except Exception as e:
        raise GithubException(f"Could not confirm access to the GitHub API: {str(e)}")


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
    json_list = response.json()

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


def find_latest_release(repo, include_beta=None):
    try:
        if include_beta:
            return next(repo.releases())
        else:
            return repo.latest_release()
    except (github3.exceptions.NotFoundError, StopIteration):
        pass


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


def create_gist(github, description, files):
    """Creates a gist with the given description and files.

    github - an
    description - str
    files - A dict of files in the form of {filename:{'content': content},...}
    """
    return github.create_gist(description, files, public=False)
