from http.client import HTTPMessage
import io
import unittest

import mock

from cumulusci.core.github import get_github_api


class MockHttpResponse(mock.Mock):

    def __init__(self, status):
        super(MockHttpResponse, self).__init__()
        self.status = status
        self.strict = 0
        self.version = 0
        self.reason = None
        self.msg = HTTPMessage(io.BytesIO())

    def read(self):
        return b''

    def isclosed(self):
        return True


class TestGithub(unittest.TestCase):

    @mock.patch('urllib3.connectionpool.HTTPConnectionPool._make_request')
    def test_github_api_retries(self, _make_request):
        gh = get_github_api('TestUser', 'TestPass')
        adapter = gh._session.get_adapter('http://')

        self.assertEqual(0.3, adapter.max_retries.backoff_factor)
        self.assertIn(502, adapter.max_retries.status_forcelist)

        _make_request.side_effect = [
            MockHttpResponse(status=503),
            MockHttpResponse(status=200),
        ]

        gh.octocat('meow')
        self.assertEqual(_make_request.call_count, 2)
