import http.client
import logging
import os
import random
import re
import socket
import ssl
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Optional, Union
from urllib.parse import parse_qs, quote, urlparse

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pydantic import BaseModel

from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.oauth.exceptions import OAuth2Error
from cumulusci.utils.http.requests_utils import safe_json_from_response

logger = logging.getLogger(__name__)

HTTP_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
SANDBOX_DOMAIN_RE = re.compile(
    r"^https://([\w\d-]+\.)?(test|cs\d+)(\.my)?\.salesforce\.com/?$"
)
SANDBOX_LOGIN_URL = (
    os.environ.get("SF_SANDBOX_LOGIN_URL") or "https://test.salesforce.com"
)
PROD_LOGIN_URL = os.environ.get("SF_PROD_LOGIN_URL") or "https://login.salesforce.com"
PORT_IN_USE_ERR = "Cannot listen for callback, as port {} is already in use."
DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


def create_key_and_self_signed_cert():
    """Create both a localhost.pem and key.pem file"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Salesforce.com"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now())
        .not_valid_after(datetime.now() + timedelta(hours=1))
        .sign(key, hashes.SHA256())
    )
    with open("localhost.pem", "w") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM).decode("latin1"))

    with open("key.pem", "w") as f:
        f.write(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            ).decode("latin1")
        )


class OAuth2ClientConfig(BaseModel):
    client_id: str
    client_secret: Optional[str] = None
    auth_uri: str
    token_uri: str
    redirect_uri: Optional[str] = None
    scope: Optional[str] = None


class OAuth2DeviceConfig(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: Optional[str] = None
    expires_in: int
    interval: int
    grant_type: str = DEVICE_GRANT_TYPE


class OAuth2Client(object):
    """Represents an OAuth2 client with the ability to
    execute different grant types.
    Currently supported grant types include:
        (1) Authorization Code  - via auth_code_flow()
        (2) Refresh Token       - via refresh_token()
    """

    response: Optional[requests.Response]

    def __init__(self, client_config: Union[OAuth2ClientConfig, Dict]):
        if isinstance(client_config, dict):
            client_config = OAuth2ClientConfig(**client_config)
        self.client_config = client_config
        self.response = None
        self.httpd = None
        self.httpd_timeout = 300

    def auth_code_flow(self, **kwargs) -> dict:
        """Completes the flow for the OAuth2 auth code grant type.
        For more info on the auth code flow see:
        https://www.oauth.com/oauth2-servers/server-side-apps/authorization-code/

        @param auth_info instanace of OAuthInfo to use in the flow
        @returns a dict of values returned from the auth server.
        It will be similar in shape to:
        {
            "access_token":"<access_token>",
            "token_type":"bearer",
            "expires_in":3600,
            "refresh_token":"<refresh_token>",
            "scope":"create"
        }
        """
        assert self.client_config.redirect_uri
        auth_uri_with_params = self._get_auth_uri(**kwargs)
        # Open up an http daemon to listen for the
        # callback from the auth server
        self.httpd = self._create_httpd()
        logger.info(
            f"Spawning HTTP server at {self.client_config.redirect_uri}"
            f" with timeout of {self.httpd.timeout} seconds.\n"
            "If you are unable to log in to Salesforce you can"
            " press <Ctrl+C> to kill the server and return to the command line."
        )
        # Open a browser and direct the user to login
        webbrowser.open(auth_uri_with_params, new=1)
        # Implement the 300 second timeout
        timeout_thread = HTTPDTimeout(self.httpd, self.httpd_timeout)
        timeout_thread.start()
        # use serve_forever because it is smarter about polling for Ctrl-C
        # on Windows.
        #
        # There are two ways it can be shutdown.
        # 1. Get a callback from Salesforce.
        # 2. Timeout

        old_timeout = socket.getdefaulttimeout()
        try:
            # for some reason this is required for Safari (checked Feb 2021)
            # https://github.com/SFDO-Tooling/CumulusCI/pull/2373
            socket.setdefaulttimeout(3)
            self.httpd.serve_forever()
        finally:
            socket.setdefaulttimeout(old_timeout)
            if self.client_config.redirect_uri.startswith("https:"):
                Path("key.pem").unlink()
                Path("localhost.pem").unlink()

        # timeout thread can stop polling and just finish
        timeout_thread.quit()
        self.validate_response(self.response)
        return safe_json_from_response(self.response)

    def _get_auth_uri(self, **kwargs):
        url = self.client_config.auth_uri
        url += "?response_type=code"
        url += f"&client_id={self.client_config.client_id}"
        url += f"&redirect_uri={self.client_config.redirect_uri}"
        if self.client_config.scope:
            url += f"&scope={quote(self.client_config.scope)}"
        for k, v in kwargs.items():
            url += f"&{k}={quote(v)}"
        return url

    def _create_httpd(self):
        """Create an http daemon process to listen
        for the callback from the auth server"""
        url_parts = urlparse(self.client_config.redirect_uri)
        use_https = url_parts.scheme == "https"
        hostname = url_parts.hostname
        port = url_parts.port

        server_address = (hostname, port)
        OAuthCallbackHandler.parent = self

        try:
            httpd = HTTPServer(server_address, OAuthCallbackHandler)
        except OSError as e:
            if self._address_in_use_error(e):
                raise OAuth2Error(PORT_IN_USE_ERR.format(port))
            else:
                raise

        if use_https:
            if not Path("localhost.pem").is_file() or not Path("key.pem").is_file():
                create_key_and_self_signed_cert()
            httpd.socket = ssl.wrap_socket(
                httpd.socket,
                server_side=True,
                certfile="localhost.pem",
                keyfile="key.pem",
                ssl_version=ssl.PROTOCOL_TLS,
            )

        httpd.timeout = self.httpd_timeout
        return httpd

    def _address_in_use_error(self, error: Exception):
        """Returns true if the error is caused by an 'address already in use'.
        This presents differently based on the OS."""
        # osx, linux, windows
        error_codes = (48, 98, 10048)
        return True if error.errno in error_codes else False

    def auth_code_grant(self, auth_code):
        """Exchange an auth code for an access token"""
        data = {
            "client_id": self.client_config.client_id,
            "client_secret": self.client_config.client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": self.client_config.redirect_uri,
            "code": auth_code,
        }
        return requests.post(
            self.client_config.token_uri, headers=HTTP_HEADERS, data=data
        )

    def refresh_token(self, refresh_token):
        data = {
            "client_id": self.client_config.client_id,
            "client_secret": self.client_config.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        response = requests.post(
            self.client_config.token_uri, headers=HTTP_HEADERS, data=data
        )
        self.validate_response(response)
        return safe_json_from_response(response)

    def validate_response(self, response):
        """Subclasses can implement custom response validation"""
        if response is None:
            raise CumulusCIUsageError("Authentication timed out or otherwise failed.")
        elif response.status_code == http.client.OK:
            return
        raise OAuth2Error(
            f"OAuth failed\nstatus_code: {response.status_code}\ncontent: {response.content}"
        )


class HTTPDTimeout(threading.Thread):
    """Establishes a timeout for a SimpleHTTPServer"""

    # allow the process to quit even if the
    # timeout thread is still alive
    daemon = True

    def __init__(self, httpd, timeout):
        self.httpd = httpd
        self.timeout = timeout
        super().__init__()

    def run(self):
        """Check every second for HTTPD or quit after timeout"""
        target_time = time.time() + self.timeout
        while time.time() < target_time:
            time.sleep(1)
            if not self.httpd:
                break

        # extremely minor race condition
        if self.httpd:  # pragma: no cover
            self.httpd.shutdown()

    def quit(self):
        """Quit before timeout"""
        self.httpd = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    parent: Optional[OAuth2Client] = None

    def do_GET(self):
        args = parse_qs(urlparse(self.path).query, keep_blank_values=True)

        if "error" in args:
            http_status = http.client.BAD_REQUEST
            http_body = f"error: {args['error'][0]}\nerror description: {args['error_description'][0]}"
        else:
            http_status = http.client.OK
            emoji = random.choice(["🎉", "👍", "👍🏿", "🥳", "🎈"])
            http_body = f"""<html>
            <h1 style="font-size: large">{emoji}</h1>
            <p>Congratulations! Your authentication succeeded.</p>"""
            auth_code = args["code"]
            self.parent.response = self.parent.auth_code_grant(auth_code)
            if self.parent.response.status_code >= http.client.BAD_REQUEST:
                http_status = self.parent.response.status_code
                http_body = self.parent.response.text
        self.send_response(http_status)
        self.send_header("Content-Type", "text/html; charset=utf-8")

        self.end_headers()
        self.wfile.write(http_body.encode("utf-8"))
        if self.parent.response is None:
            response = requests.Response()
            response.status_code = http_status
            response._content = http_body
            self.parent.response = response

        #  https://docs.python.org/3/library/socketserver.html#socketserver.BaseServer.shutdown
        # shutdown() must be called while serve_forever() is running in a different thread otherwise it will deadlock.
        threading.Thread(target=self.server.shutdown).start()


def get_device_code(config: OAuth2ClientConfig) -> dict:
    """Initiates the flow for the OAuth2 device authorization grant type.
    For more info on the auth code flow see:
    https://datatracker.ietf.org/doc/html/rfc8628

    @param config instanace of OAuth2ClientConfig to use in the flow
    @returns a dict of values returned from the auth server.
    It will be similar in shape to:
    {
        "device_code":"<device_verification_code>",
        "user_code":"<user_verification_code>",
        "verification_uri": <end_user_verification_uri>,
        "verification_uri_complete": <end_user_verification_uri+user_code>,
        "expires_in":3600,
        "interval": 5
    }
    """
    data = config.dict(include={"client_id", "scope"})
    response = requests.post(
        config.auth_uri, data=data, headers={"Accept": "application/json"}
    )
    response.raise_for_status()
    return response.json()


def get_device_oauth_token(
    client_config: OAuth2ClientConfig, device_config: OAuth2DeviceConfig
) -> dict:
    """Polls the authorization server for user authorization.

    @param client_config client settings, including token_uri, the URI to poll
    @param device_config server settings, including the device_code returned
    from the auth server.
    @returns a dict including the access token.
    {
        "access_token": "gho_16C7e42F292c6912E7710c838347Ae178B4a",
        "token_type": "bearer",
        "scope": "user"
    }
    """
    data = device_config.dict(include={"device_code", "grant_type"})
    data["client_id"] = client_config.client_id

    AUTH_PENDING_ERROR = "authorization_pending"
    SLOW_DOWN_ERROR = "slow_down"
    response_dict = {}
    time_remaining = device_config.expires_in

    while time_remaining > 0:
        response = requests.post(
            client_config.token_uri, data=data, headers={"Accept": "application/json"}
        )
        response_dict = response.json()
        response.raise_for_status()  # Expected errors' status is 200

        if "access_token" in response_dict:
            break

        if response_dict["error"] in (SLOW_DOWN_ERROR, AUTH_PENDING_ERROR):
            # server backoff
            wait_secs = response_dict.get("interval", device_config.interval)
            # If waiting on the user, wait some more.
            time_remaining -= wait_secs
            time.sleep(wait_secs)
        else:
            # Some other error has occurred, so
            handle_device_token_request_error(response_dict)

    return response_dict


def handle_device_token_request_error(response_dict: dict) -> None:
    error_code = response_dict["error"]
    error_msgs = {"expired_token": "Please retry."}
    raise OAuth2Error(
        f"Authorization failed, error code: {error_code}, {error_msgs.get(error_code)}. See: {response_dict['error_uri']}"
    )
