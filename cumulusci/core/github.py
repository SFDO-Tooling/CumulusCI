"""Wraps the github3 library to configure request retries."""

from future import standard_library

standard_library.install_aliases()
from builtins import str
from future.utils import native_str_to_bytes
from cumulusci.core.exceptions import GithubException
from github3 import GitHub
from github3 import login
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import github3
import os

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


def get_github_api_for_repo(keychain, owner, repo):
    gh = GitHub()
    # Apply retry policy
    gh.session.mount("http://", adapter)
    gh.session.mount("https://", adapter)

    APP_KEY = native_str_to_bytes(os.environ.get("GITHUB_APP_KEY", ""))
    APP_ID = os.environ.get("GITHUB_APP_ID")
    if APP_ID and APP_KEY:
        installation = INSTALLATIONS.get((owner, repo))
        if installation is None:
            gh.login_as_app(APP_KEY, APP_ID, expire_in=120)
            try:
                installation = gh.app_installation_for_repository(owner, repo)
            except github3.exceptions.NotFoundError:
                raise GithubException(
                    "Could not access {}/{} using GitHub app. "
                    "Does the app need to be installed for this repository?".format(
                        owner, repo
                    )
                )
            INSTALLATIONS[(owner, repo)] = installation
        gh.login_as_app_installation(APP_KEY, APP_ID, installation.id)
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
        raise GithubException(
            "Could not confirm access to the GitHub API: {}".format(str(e))
        )


def get_pull_requests_with_base_branch(repo, base_branch_name, head=None):
    """Returns a list of pull requests with the given base branch"""
    if head:
        head = repo.owner.login + ":" + head
    return list(repo.pull_requests(base=base_branch_name, head=head))


def get_pull_requests_by_head(repo, branch_name):
    """Returns all pull requests with head equal to the given branch name."""
    if branch_name == repo.default_branch:
        return None

    return list(repo.pull_requests(head=repo.owner.login + ":" + branch_name))


def create_pull_request(repo, branch_name, base=None, title=None):
    """Creates a pull request for the given branch"""
    base = base or "master"
    title = title or "Auto-Generated Pull Request"
    pull_request = repo.create_pull(title, base, branch_name)
    return pull_request


def add_labels_to_pull_request(repo, pull_request, *labels):
    """Adds a label to a pull request via the issue object
        Args:
            repo: Repository object
            pull_request: ShortPullRequest object that exists in repo
            labels: list(str) of labels to add to the pull request"""
    issue = repo.issue(pull_request.number)
    issue.add_labels(*labels)


def is_label_on_pull_request(repo, pull_request, label_name):
    """Returns True if the given label is on the pull request with the given
    pull request number. False otherwise."""
    labels = list(repo.issue(pull_request.number).labels())
    return any(label_name == issue_label.name for issue_label in labels)
