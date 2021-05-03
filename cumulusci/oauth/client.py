from cumulusci.oauth.exceptions import OAuthError
from cumulusci.core.exceptions import CumulusCIUsageError
import http.client
import logging
import os
import re
import requests
import random
import socket
import threading
import time
import webbrowser

from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from urllib.parse import parse_qs
from urllib.parse import quote
from urllib.parse import urlparse

from cumulusci.oauth.client_info import OAuthClientInfo
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


class OAuth2Client(object):
    """Represents an OAuth2 client with the ability to
    execute different grant types.
    Currenntly supported grant types include:
        (1) Authorization Code - via auth_code_flow()

    To instantiate, just provide an instance or subclass
    of OAuthClientInfo to the contructor.
    """

    def __init__(self, client_info: OAuthClientInfo):
        self.client_info = client_info
        self.response = None
        self.httpd = None
        self.httpd_timeout = 300

    def auth_code_flow(self) -> None:
        """Completes the flow for the OAuth2 auth code grant type.
        For more info on the auth code flow see:
        https://www.oauth.com/oauth2-servers/server-side-apps/authorization-code/

        @param auth_info instanace of OAuthInfo to use in the flow
        @returns a dict of values returned from the auth server.
        It will be similar in shape to:
        {
            "access_token":"<acces_token>",
            "token_type":"bearer",
            "expires_in":3600,
            "refresh_token":"<refresh_token>",
            "scope":"create"
        }
        """
        auth_uri_with_params = self._get_auth_uri()
        # Open a browser and direct the user to login
        webbrowser.open(auth_uri_with_params, new=1)
        # Open up an http deamon to listen for the
        # callback from the auth server
        self.httpd = self._create_httpd()
        logger.info(
            f"Spawning HTTP server at {self.client_info.callback_url}"
            f" with timeout of {self.httpd.timeout} seconds.\n"
            "If you are unable to log in to Salesforce you can"
            " press <Ctrl+C> to kill the server and return to the command line."
        )
        # Implement the 300 second timeout
        timeout_thread = HTTPDTimeout(self.httpd, self.httpd_timeout)
        timeout_thread.start()
        # use serve_forever because it is smarter about polling for Ctrl-C
        # on Windows.
        #
        # There are two ways it can be shutdown.
        # 1. Get a callback from Salesforce.
        # 2. Timeout

        try:
            # for some reason this is required for Safari (checked Feb 2021)
            # https://github.com/SFDO-Tooling/CumulusCI/pull/2373
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(3)
            self.httpd.serve_forever()
        finally:
            socket.setdefaulttimeout(old_timeout)

        # timeout thread can stop polling and just finish
        timeout_thread.quit()
        self.validate_response(self.response)
        return safe_json_from_response(self.response)

    def _get_auth_uri(self, is_salesforce=False):
        url = self.client_info.auth_uri
        url += "?response_type=code"
        url += f"&client_id={self.client_info.client_id}"
        url += f"&redirect_uri={self.client_info.callback_url}"
        url += f"&scope={quote(self.client_info.scope)}"
        if is_salesforce:
            url += f"&prompt={quote('login')}"
        return url

    def _create_httpd(self):
        """Create an http deamon process to listen
        for the callback from the auth server"""
        url_parts = urlparse(self.client_info.callback_url)
        server_address = (url_parts.hostname, url_parts.port)
        OAuthCallbackHandler.parent = self
        httpd = HTTPServer(server_address, OAuthCallbackHandler)
        httpd.timeout = self.httpd_timeout
        return httpd

    def get_access_token(self, auth_code):
        """Exchange an auth code for an access token"""
        data = {
            "client_id": self.client_info.client_id,
            "client_secret": self.client_info.client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": self.client_info.callback_url,
            "code": auth_code,
        }
        return requests.post(
            self.client_info.token_uri, headers=HTTP_HEADERS, data=data
        )

    def refresh_token(self, refresh_token):
        data = {
            "client_id": self.client_info.client_id,
            "client_secret": self.client_info.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        token_uri = self.client_info.token_uri
        return requests.post(token_uri, headers=HTTP_HEADERS, data=data)

    def revoke_token(self, access_token):
        data = {"token": quote(access_token)}
        revoke_uri = self.client_info.revoke_uri
        response = requests.post(revoke_uri, headers=HTTP_HEADERS, data=data)
        response.raise_for_status()
        return response

    def validate_response(self, response):
        """Subclasses can implement custom response validation"""
        if not response:
            raise CumulusCIUsageError("Authentication timed out or otherwise failed.")
        elif response.status_code == http.client.OK:
            return
        raise OAuthError(
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

        if self.httpd:  # extremely minor race condition
            self.httpd.shutdown()

    def quit(self):
        """Quit before timeout"""
        self.httpd = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    parent = None

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
            self.parent.response = self.parent.get_access_token(auth_code)
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
