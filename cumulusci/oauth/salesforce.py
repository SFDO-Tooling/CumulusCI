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

from cumulusci.oauth.exceptions import SalesforceOAuthError

HTTP_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
SANDBOX_DOMAIN_RE = re.compile(
    r"^https://([\w\d-]+\.)?(test|cs\d+)(\.my)?\.salesforce\.com/?$"
)
SANDBOX_LOGIN_URL = (
    os.environ.get("SF_SANDBOX_LOGIN_URL") or "https://test.salesforce.com"
)
PROD_LOGIN_URL = os.environ.get("SF_PROD_LOGIN_URL") or "https://login.salesforce.com"


def jwt_session(client_id, private_key, username, url=None):
    """Complete the JWT Token Oauth flow to obtain an access token for an org.

    :param client_id: Client Id for the connected app
    :param private_key: Private key used to sign the connected app's certificate
    :param username: Username to authenticate as
    :param url: Org's instance_url
    """
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
        "aud": aud,  # jwt aud is NOT mydomain
        "exp": timegm(datetime.utcnow().utctimetuple()),
    }
    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": encoded_jwt,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    auth_url = urljoin(url, "services/oauth2/token")
    response = requests.post(url=auth_url, data=data, headers=headers)
    response.raise_for_status()
    return response.json()


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


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    parent = None

    def do_GET(self):
        args = parse_qs(urlparse(self.path).query, keep_blank_values=True)
        if "error" in args:
            http_status = http.client.BAD_REQUEST
            http_body = f"error: {args['error'][0]}\nerror description: {args['error_description'][0]}"
        else:
            http_status = http.client.OK
            http_body = "Congratulations! Your authentication succeeded."
            code = args["code"]
            self.parent.response = self.parent.oauth_api.get_token(code)
            if self.parent.response.status_code >= http.client.BAD_REQUEST:
                http_status = self.parent.response.status_code
                http_body = self.parent.response.text
        self.send_response(http_status)
        self.end_headers()
        self.wfile.write(http_body.encode("ascii"))
        if self.parent.response is None:
            response = requests.Response()
            response.status_code = http_status
            response._content = http_body
            self.parent.response = response


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
        self.httpd.handle_request()
        self._check_response(self.response)
        return self.response.json()

    def _check_response(self, response):
        if response.status_code == http.client.OK:
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
