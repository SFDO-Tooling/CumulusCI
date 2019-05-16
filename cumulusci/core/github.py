"""Wraps the github3 library to configure request retries."""

from cumulusci.core.exceptions import GithubException
from github3 import login
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

retries = Retry(status_forcelist=(502, 503, 504), backoff_factor=0.3)
adapter = HTTPAdapter(max_retries=retries)


def get_github_api(username, password):
    gh = login(username, password)
    gh.session.mount("http://", adapter)
    gh.session.mount("https://", adapter)
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
