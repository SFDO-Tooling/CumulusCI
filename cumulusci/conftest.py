import io
import os
from http.client import HTTPMessage
from unittest import mock

from pytest import fixture
from cumulusci.core.github import get_github_api
from cumulusci.tests.pytest_plugins.pytest_sf_vcr import vcr_config, salesforce_vcr
from cumulusci.tests.util import DummyOrgConfig


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
            {
                "instance_url": "https://orgname.salesforce.com",
                "access_token": "pytest_sf_orgconnect_abc123",
                "id": "ORGID/ORGID",
            },
            "pytest_sf_orgconnect_dummy_orgconfig",
        )

    return fallback_orgconfig


vcr_config = fixture(vcr_config, scope="module")
vcr = fixture(salesforce_vcr, scope="module")
