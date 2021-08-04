import http.client
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from unittest import mock

import pytest
import responses
from requests.models import Response

from cumulusci.core.exceptions import SalesforceCredentialsException
from cumulusci.core.keychain.base_project_keychain import DEFAULT_CONNECTED_APP_PORT
from cumulusci.oauth.client import PORT_IN_USE_ERR, OAuth2Client
from cumulusci.oauth.exceptions import OAuth2Error
from cumulusci.oauth.salesforce import jwt_session


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


@pytest.fixture
def client_config():
    return {
        "client_id": "foo_id",
        "client_secret": "foo_secret",
        "auth_uri": "https://login.salesforce.com/services/oauth2/authorize",
        "token_uri": "https://login.salesforce.com/services/oauth2/token",
        "redirect_uri": "http://localhost:7788/callback",
        "scope": "web full refresh_token",
        "prompt": "login",
    }


@pytest.fixture
def client(client_config):
    return OAuth2Client(client_config)


@pytest.fixture
def http_client(client_config):
    client_config = client_config.copy()
    client_config["redirect_uri"] = "http://localhost:8080/callback"
    return OAuth2Client(client_config)


@contextmanager
@mock.patch("time.sleep", time.sleep)  # undo mock from conftest
def httpd_thread(oauth_client):
    # call OAuth object on another thread - this spawns local httpd
    thread = threading.Thread(target=oauth_client.auth_code_flow)
    thread.start()
    while thread.is_alive():
        if oauth_client.httpd:
            break
        time.sleep(0.01)

    assert (
        oauth_client.httpd
    ), "HTTPD did not start. Perhaps port 8080 cannot be accessed."

    try:
        yield oauth_client
    finally:
        oauth_client.httpd.shutdown()
        thread.join()


@mock.patch("webbrowser.open", mock.MagicMock(return_value=None))
class TestOAuth2Client:
    @responses.activate
    def test_refresh_token(self, client):
        responses.add(
            responses.POST,
            "https://login.salesforce.com/services/oauth2/token",
            body=b'{"message":"SENTINEL"}',
        )
        info = client.refresh_token("token")
        assert "SENTINEL" == info["message"]

    @responses.activate
    def test_auth_code_flow___http(self, http_client):
        expected_response = {
            "access_token": "abc123",
            "id_token": "abc123",
            "token_type": "Bearer",
            "signature": "abc123",
            "issued_at": "12345",
            "scope": "web full refresh_token",
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

        # call OAuth object on another thread - this spawns local httpd
        with httpd_thread(http_client) as oauth_client:
            # simulate callback from browser
            response = urllib.request.urlopen(
                http_client.client_config.redirect_uri + "?code=123"
            )

        assert oauth_client.response.json() == expected_response
        assert b"Congratulations" in response.read()

    @responses.activate
    def test_auth_code_flow___https(self, client):
        expected_response = {
            "access_token": "abc123",
            "id_token": "abc123",
            "token_type": "Bearer",
            "signature": "abc123",
            "issued_at": "12345",
            "scope": "web full refresh_token",
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
        # use https for callback
        client.client_config.redirect_uri = "https://localhost:8080/callback"
        # squash CERTIFICATE_VERIFY_FAILED from urllib
        # https://stackoverflow.com/questions/49183801/ssl-certificate-verify-failed-with-urllib
        ssl._create_default_https_context = ssl._create_unverified_context

        # call OAuth object on another thread - this spawns local httpd
        with httpd_thread(client) as oauth_client:
            # simulate callback from browser
            response = urllib.request.urlopen(
                oauth_client.client_config.redirect_uri + "?code=123"
            )

        assert oauth_client.response.json() == expected_response
        assert b"Congratulations" in response.read()

    @responses.activate
    def test_oauth_flow_error_from_auth(self, client):
        # mock response for SalesforceOAuth2.get_token()
        expected_response = {
            "access_token": "abc123",
            "id_token": "abc123",
            "token_type": "Bearer",
            "signature": "abc123",
            "issued_at": "12345",
            "scope": "web full refresh_token",
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

        # call OAuth object on another thread - this spawns local httpd
        with httpd_thread(client):
            # simulate callback from browser
            with pytest.raises(urllib.error.HTTPError):
                urllib.request.urlopen(
                    client.client_config.redirect_uri
                    + "?error=123&error_description=broken"
                )

    @pytest.mark.skipif(
        sys.platform.startswith("win"), reason="setup differs from windows"
    )
    def test_create_httpd__port_already_in_use(self, client):
        with httpd_thread(client):
            with pytest.raises(
                OAuth2Error, match=PORT_IN_USE_ERR.format(DEFAULT_CONNECTED_APP_PORT)
            ):
                client._create_httpd()

    @mock.patch("cumulusci.oauth.client.HTTPServer")
    def test_create_httpd__other_OSError(self, HTTPServer, client):
        message = "generic error message"
        HTTPServer.side_effect = OSError(message)
        with pytest.raises(OSError, match=message):
            client._create_httpd()

    @responses.activate
    def test_oauth_flow_error_from_token(self, client):
        # mock response for OAuth2Client.get_access_token()
        responses.add(
            responses.POST,
            "https://login.salesforce.com/services/oauth2/token",
            status=http.client.FORBIDDEN,
        )

        # call OAuth object on another thread - this spawns local httpd
        with httpd_thread(client):
            # simulate callback from browser
            with pytest.raises(urllib.error.HTTPError):
                urllib.request.urlopen(client.client_config.redirect_uri + "?code=123")

    def test_validate_response__raises_error(self, client):
        response = Response()
        response.status_code = 400
        with pytest.raises(OAuth2Error):
            client.validate_response(response)
