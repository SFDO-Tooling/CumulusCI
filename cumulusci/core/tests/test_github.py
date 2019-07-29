from datetime import datetime
from http.client import HTTPMessage
import io
import os
import unittest

from github3.session import AppInstallationTokenAuth
import mock
import responses

from cumulusci.core.exceptions import CumulusCIFailure
from cumulusci.core import github
from cumulusci.core.github import get_github_api
from cumulusci.core.github import get_github_api_for_repo
from cumulusci.core.github import validate_service


class MockHttpResponse(mock.Mock):
    def __init__(self, status):
        super(MockHttpResponse, self).__init__()
        self.status = status
        self.strict = 0
        self.version = 0
        self.reason = None
        self.msg = HTTPMessage(io.BytesIO())

    def read(self):
        return b""

    def isclosed(self):
        return True


class TestGithub(unittest.TestCase):
    def tearDown(self):
        # clear cached repo -> installation mapping
        github.INSTALLATIONS.clear()

    @mock.patch("urllib3.connectionpool.HTTPConnectionPool._make_request")
    def test_github_api_retries(self, _make_request):
        gh = get_github_api("TestUser", "TestPass")
        adapter = gh.session.get_adapter("http://")

        self.assertEqual(0.3, adapter.max_retries.backoff_factor)
        self.assertIn(502, adapter.max_retries.status_forcelist)

        _make_request.side_effect = [
            MockHttpResponse(status=503),
            MockHttpResponse(status=200),
        ]

        gh.octocat("meow")
        self.assertEqual(_make_request.call_count, 2)

    @responses.activate
    @mock.patch("github3.apps.create_token")
    def test_get_github_api_for_repo(self, create_token):
        create_token.return_value = "ATOKEN"
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/installation",
            json={
                "id": 1,
                "access_tokens_url": "",
                "account": "",
                "app_id": "",
                "created_at": "",
                "events": "",
                "html_url": "",
                "permissions": "",
                "repositories_url": "",
                "repository_selection": "",
                "single_file_name": "",
                "target_id": "",
                "target_type": "",
                "updated_at": "",
            },
        )
        responses.add(
            "POST",
            "https://api.github.com/app/installations/1/access_tokens",
            status=201,
            json={"token": "ITOKEN", "expires_at": datetime.now().isoformat()},
        )

        with mock.patch.dict(
            os.environ, {"GITHUB_APP_KEY": "bogus", "GITHUB_APP_ID": "1234"}
        ):
            gh = get_github_api_for_repo(None, "TestOwner", "TestRepo")
            assert isinstance(gh.session.auth, AppInstallationTokenAuth)

    @responses.activate
    @mock.patch("github3.apps.create_token")
    def test_get_github_api_for_repo__not_installed(self, create_token):
        create_token.return_value = "ATOKEN"
        responses.add(
            "GET",
            "https://api.github.com/repos/TestOwner/TestRepo/installation",
            status=404,
        )
        with mock.patch.dict(
            os.environ, {"GITHUB_APP_KEY": "bogus", "GITHUB_APP_ID": "1234"}
        ):
            with self.assertRaises(CumulusCIFailure):
                get_github_api_for_repo(None, "TestOwner", "TestRepo")

    @responses.activate
    def test_validate_service(self):
        responses.add("GET", "https://api.github.com/rate_limit", status=401)
        with self.assertRaises(CumulusCIFailure):
            validate_service({"username": "BOGUS", "password": "BOGUS"})
