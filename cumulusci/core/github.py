"""Wraps the github3 library to configure request retries."""

from future import standard_library

standard_library.install_aliases()
from builtins import str
from future.utils import native_str_to_bytes
from cumulusci.core.exceptions import CumulusCIFailure
from github3 import GitHub
from github3 import login
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import github3
import os

retries = Retry(status_forcelist=(502, 503, 504), backoff_factor=0.3)
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
            gh.login_as_app(APP_KEY, APP_ID)
            try:
                installation = gh.app_installation_for_repository(owner, repo)
            except github3.exceptions.NotFoundError:
                raise CumulusCIFailure(
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
        raise CumulusCIFailure(
            "Could not confirm access to the GitHub API: {}".format(str(e))
        )
