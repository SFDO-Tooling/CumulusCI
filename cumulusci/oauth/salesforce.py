from calendar import timegm
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
import http.client
import jwt
import os
import re
import requests
from urllib.parse import quote
from urllib.parse import parse_qs
from urllib.parse import urljoin
from urllib.parse import urlparse
import webbrowser
import threading
import random
import time
import socket

from cumulusci.oauth.exceptions import SalesforceOAuthError
from cumulusci.core.exceptions import CumulusCIException, CumulusCIUsageError
from cumulusci.utils.http.requests_utils import safe_json_from_response

HTTP_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
SANDBOX_DOMAIN_RE = re.compile(
    r"^https://([\w\d-]+\.)?(test|cs\d+)(\.my)?\.salesforce\.com/?$"
)
SANDBOX_LOGIN_URL = (
    os.environ.get("SF_SANDBOX_LOGIN_URL") or "https://test.salesforce.com"
)
PROD_LOGIN_URL = os.environ.get("SF_PROD_LOGIN_URL") or "https://login.salesforce.com"

ERROR_MESSAGE_400 = (
    "Error: 400 status code received attempting to obtain access token: {}"
)


def jwt_session(client_id, private_key, username, url=None, auth_url=None):
    """Complete the JWT Token Oauth flow to obtain an access token for an org.

    :param client_id: Client Id for the connected app
    :param private_key: Private key used to sign the connected app's certificate
    :param username: Username to authenticate as
    :param url: Org's instance_url
    """
    if auth_url:
        aud = (
            SANDBOX_LOGIN_URL
            if auth_url.startswith(SANDBOX_LOGIN_URL)
            else PROD_LOGIN_URL
        )
    else:
        aud = PROD_LOGIN_URL
        if url is None:
            url = PROD_LOGIN_URL
        else:
            m = SANDBOX_DOMAIN_RE.match(url)
            if m is not None:
                # sandbox
                aud = SANDBOX_LOGIN_URL
                # There can be a delay in syncing scratch org credentials
                # between instances, so let's use the specific one for this org.
                instance = m.group(2)
                url = f"https://{instance}.salesforce.com"

    payload = {
        "alg": "RS256",
        "iss": client_id,
        "sub": username,
        "aud": aud,
        "exp": timegm(datetime.utcnow().utctimetuple()),
    }
    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": encoded_jwt,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_url = urljoin(url, "services/oauth2/token")
    response = requests.post(url=token_url, data=data, headers=headers)
    if response.status_code == 400:
        raise CumulusCIException(ERROR_MESSAGE_400.format(response.text))

    return safe_json_from_response(response)


class SalesforceOAuth2(object):
    def __init__(
        self,
        client_id,
        client_secret,
        callback_url,
        auth_site="https://login.salesforce.com",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url
        self.auth_site = auth_site

    def _request_token(self, request_data):
        url = self.auth_site + "/services/oauth2/token"
        data = {"client_id": self.client_id, "client_secret": self.client_secret}
        data.update(request_data)
        return requests.post(url, headers=HTTP_HEADERS, data=data)

    def get_authorize_url(self, scope, prompt=None):
        url = self.auth_site + "/services/oauth2/authorize"
        url += "?response_type=code"
        url += f"&client_id={self.client_id}"
        url += f"&redirect_uri={self.callback_url}"
        url += f"&scope={quote(scope)}"
        if prompt:
            url += f"&prompt={quote(prompt)}"
        return url

    def get_token(self, code):
        data = {
            "grant_type": "authorization_code",
            "redirect_uri": self.callback_url,
            "code": code,
        }
        return self._request_token(data)

    def refresh_token(self, refresh_token):
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        return self._request_token(data)

    def revoke_token(self, current_token):
        url = self.auth_site + "/services/oauth2/revoke"
        data = {"token": quote(current_token)}
        response = requests.post(url, headers=HTTP_HEADERS, data=data)
        response.raise_for_status()
        return response


class HTTPDTimeout(threading.Thread):
    "Establishes a timeout for a SimpleHTTPServer"
    daemon = True  # allow the process to quit even if the timeout thread
    # is still alive

    def __init__(self, httpd, timeout):
        self.httpd = httpd
        self.timeout = timeout
        super().__init__()

    def run(self):
        "Check every second for HTTPD or quit after timeout"
        target_time = time.time() + self.timeout
        while time.time() < target_time:
            time.sleep(1)
            if not self.httpd:
                break

        if self.httpd:  # extremely minor race condition
            self.httpd.shutdown()

    def quit(self):
        "Quit before timeout"
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
            code = args["code"]
            self.parent.response = self.parent.oauth_api.get_token(code)
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


class CaptureSalesforceOAuth(object):
    def __init__(self, client_id, client_secret, callback_url, auth_site, scope):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url
        self.auth_site = auth_site
        self.httpd = None
        self.oauth_api = self._get_oauth_api()
        self.response = None
        self.scope = scope
        self.httpd_timeout = 300

    def __call__(self):
        url = self._get_redirect_url()
        self._launch_browser(url)
        self._create_httpd()
        print(
            f"Spawning HTTP server at {self.callback_url} with timeout of {self.httpd.timeout} seconds.\n"
            + "If you are unable to log in to Salesforce you can "
            + "press ctrl+c to kill the server and return to the command line."
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
        self._check_response(self.response)
        return safe_json_from_response(self.response)

    def _check_response(self, response):
        if not response:
            raise CumulusCIUsageError("Authentication timed out or otherwise failed.")
        elif response.status_code == http.client.OK:
            return
        raise SalesforceOAuthError(
            f"status_code: {response.status_code} content: {response.content}"
        )

    def _create_httpd(self):
        url_parts = urlparse(self.callback_url)
        server_address = (url_parts.hostname, url_parts.port)
        OAuthCallbackHandler.parent = self
        self.httpd = HTTPServer(server_address, OAuthCallbackHandler)
        self.httpd.timeout = self.httpd_timeout

    def _get_oauth_api(self):
        return SalesforceOAuth2(
            self.client_id, self.client_secret, self.callback_url, self.auth_site
        )

    def _get_redirect_url(self):
        url = self.oauth_api.get_authorize_url(self.scope, prompt="login")
        response = requests.get(url)
        self._check_response(response)
        return url

    def _launch_browser(self, url):
        print(f"Launching web browser for URL {url}")
        webbrowser.open(url, new=1)
