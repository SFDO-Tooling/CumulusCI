import http.client
import pytest
import responses
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

from unittest import mock

from cumulusci.core.exceptions import SalesforceCredentialsException
from cumulusci.oauth.salesforce import (
    CaptureSalesforceOAuth,
    SalesforceOAuth2,
    jwt_session,
)


@responses.activate
@mock.patch("cumulusci.oauth.salesforce.jwt.encode")
def test_jwt_session(encode):
    # Mock the call to encode so we don't need
    # to generate a private key that would be committed
    error = "Yeti"
    responses.add(
        responses.POST,
        "https://login.salesforce.com/services/oauth2/token",
        body=error,
        status=400,
    )
    with pytest.raises(
        SalesforceCredentialsException, match=f"Error retrieving access token: {error}"
    ):
        jwt_session("client_id", "server_key", "username")


class TestSalesforceOAuth(unittest.TestCase):
    def _create_oauth(self):
        return SalesforceOAuth2(
            client_id="foo_id",
            client_secret="foo_secret",
            callback_url="http://localhost:8080",
        )

    @responses.activate
    def test_refresh_token(self):
        oauth = self._create_oauth()
        responses.add(
            responses.POST,
            "https://login.salesforce.com/services/oauth2/token",
            body=b"SENTINEL",
        )
        resp = oauth.refresh_token("token")
        self.assertEqual(resp.text, "SENTINEL")

    @responses.activate
    def test_revoke_token(self):
        oauth = self._create_oauth()
        responses.add(
            responses.POST,
            "https://login.salesforce.com/services/oauth2/revoke",
            status=http.client.OK,
        )
        resp = oauth.revoke_token("token")
        self.assertEqual(200, resp.status_code)


@mock.patch("webbrowser.open", mock.MagicMock(return_value=None))
class TestCaptureSalesforceOAuth(unittest.TestCase):
    def _create_oauth(self):
        return CaptureSalesforceOAuth(
            self.client_id,
            self.client_secret,
            self.callback_url,
            self.auth_site,
            self.scope,
        )

    def setUp(self):
        self.client_id = "foo_id"
        self.client_secret = "foo_secret"
        self.callback_url = "http://localhost:8080"
        self.scope = "refresh_token web full"
        self.auth_site = "https://login.salesforce.com"

    @responses.activate
    @mock.patch("time.sleep", time.sleep)  # undo mock from conftest
    def test_oauth_flow_simple(self):

        # mock response to URL validation
        responses.add(
            responses.GET,
            "https://login.salesforce.com/services/oauth2/authorize",
            status=http.client.OK,
        )

        # mock response for SalesforceOAuth2.get_token()
        expected_response = {
            "access_token": "abc123",
            "id_token": "abc123",
            "token_type": "Bearer",
            "signature": "abc123",
            "issued_at": "12345",
            "scope": "{}".format(self.scope),
            "instance_url": "https://na15.salesforce.com",
            "id": "https://login.salesforce.com/id/abc/xyz",
            "refresh_token": "abc123",
        }
        responses.add(
            responses.POST,
            "https://login.salesforce.com/services/oauth2/token",
            status=http.client.OK,
            json=expected_response,
        )

        # create CaptureSalesforceOAuth instance
        o = self._create_oauth()

        # call OAuth object on another thread - this spawns local httpd
        t = threading.Thread(target=o.__call__)
        t.start()
        while True:
            if o.httpd:
                break
            print("waiting for o.httpd")
            time.sleep(0.01)

        # simulate callback from browser
        response = urllib.request.urlopen(self.callback_url + "?code=123")

        # wait for thread to complete
        t.join()

        # verify
        self.assertEqual(o.response.json(), expected_response)
        self.assertIn(b"Congratulations", response.read())

    @mock.patch("time.sleep", time.sleep)  # undo mock from conftest
    @responses.activate
    def test_oauth_flow_error_from_auth(self):

        # mock response to URL validation
        responses.add(
            responses.GET,
            "https://login.salesforce.com/services/oauth2/authorize",
            status=http.client.OK,
        )

        # mock response for SalesforceOAuth2.get_token()
        expected_response = {
            "access_token": "abc123",
            "id_token": "abc123",
            "token_type": "Bearer",
            "signature": "abc123",
            "issued_at": "12345",
            "scope": "{}".format(self.scope),
            "instance_url": "https://na15.salesforce.com",
            "id": "https://login.salesforce.com/id/abc/xyz",
            "refresh_token": "abc123",
        }
        responses.add(
            responses.POST,
            "https://login.salesforce.com/services/oauth2/token",
            status=http.client.OK,
            json=expected_response,
        )

        # create CaptureSalesforceOAuth instance
        o = self._create_oauth()

        # call OAuth object on another thread - this spawns local httpd
        t = threading.Thread(target=o.__call__)
        t.start()
        while True:
            if o.httpd:
                break
            print("waiting for o.httpd")
            time.sleep(0.01)

        # simulate callback from browser
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(
                self.callback_url + "?error=123&error_description=broken"
            )

        # wait for thread to complete
        t.join()

    @mock.patch("time.sleep", time.sleep)  # undo mock from conftest
    @responses.activate
    def test_oauth_flow_error_from_token(self):

        # mock response to URL validation
        responses.add(
            responses.GET,
            "https://login.salesforce.com/services/oauth2/authorize",
            status=http.client.OK,
        )

        # mock response for SalesforceOAuth2.get_token()
        responses.add(
            responses.POST,
            "https://login.salesforce.com/services/oauth2/token",
            status=http.client.FORBIDDEN,
        )

        # create CaptureSalesforceOAuth instance
        o = self._create_oauth()

        # call OAuth object on another thread - this spawns local httpd
        t = threading.Thread(target=o.__call__)
        t.start()
        while True:
            if o.httpd:
                break
            print("waiting for o.httpd")
            time.sleep(0.01)

        # simulate callback from browser
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(self.callback_url + "?code=123")

        # wait for thread to complete
        t.join()
