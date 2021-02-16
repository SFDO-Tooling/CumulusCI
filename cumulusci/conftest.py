import io
import os
from http.client import HTTPMessage
from unittest import mock
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from pytest import fixture
from cumulusci.core.github import get_github_api
from cumulusci.tests.pytest_plugins.pytest_sf_vcr import vcr_config, salesforce_vcr
from cumulusci.tests.util import DummyOrgConfig, mock_homedir, DummyKeychain
from cumulusci.tasks.salesforce.tests.util import create_task_fixture


@fixture(scope="session", autouse=True)
def mock_sleep():
    """Patch time.sleep to avoid delays in unit tests"""
    with mock.patch("time.sleep"):
        yield


class MockHttpResponse(mock.Mock):
    def __init__(self, status):
        super(MockHttpResponse, self).__init__()
        self.status = status
        self.strict = 0
        self.version = 0
        self.reason = None
        self.msg = HTTPMessage(io.BytesIO())
        self.closed = True

    def read(self):  # pragma: no cover
        return b""

    def isclosed(self):
        return self.closed


@fixture
def gh_api():
    return get_github_api("TestOwner", "TestRepo")


@fixture(scope="class", autouse=True)
def restore_cwd():
    d = os.getcwd()
    try:
        yield
    finally:
        os.chdir(d)


@fixture
def mock_http_response():
    def _make_response(status):
        return MockHttpResponse(status)

    return _make_response


@fixture(scope="session")
def fallback_orgconfig():
    def fallback_orgconfig():
        return DummyOrgConfig(
            name="pytest_sf_orgconnect_dummy_orgconfig", keychain=DummyKeychain()
        )

    return fallback_orgconfig


vcr_config = fixture(vcr_config, scope="module")
vcr = fixture(salesforce_vcr, scope="module")

create_task_fixture = fixture(create_task_fixture, scope="function")


# TODO: This should also chdir to a temp directory which
#       can represent the repo-root, but that will require
#       test case changes.
@pytest.fixture(autouse=True, scope="session")
def patch_home_and_env(request):
    "Patch the default home directory and $HOME environment for all tests at once."
    with TemporaryDirectory(prefix="fake_home_") as home, mock_homedir(home):
        Path(home, ".cumulusci").mkdir()
        Path(home, ".cumulusci/cumulusci.yml").touch()
        yield
