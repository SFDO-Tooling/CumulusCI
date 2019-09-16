from pytest import fixture
from cumulusci.core.github import get_github_api


@fixture
def gh_api():
    return get_github_api("TestOwner", "TestRepo")
