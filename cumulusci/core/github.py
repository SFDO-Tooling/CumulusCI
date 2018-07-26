"""Wraps the github3 library to configure request retries."""

from github3 import login
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

retries = Retry(
    status_forcelist=(502, 503, 504),
    backoff_factor=0.3
)
adapter = HTTPAdapter(max_retries=retries)


def get_github_api(username, password):
    gh = login(username, password)
    gh._session.mount('http://', adapter)
    gh._session.mount('https://', adapter)
    return gh
