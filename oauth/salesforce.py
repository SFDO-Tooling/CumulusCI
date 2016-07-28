from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
import httplib
import requests
from urllib import quote
from urlparse import parse_qs
from urlparse import urlparse
import webbrowser

HTTP_HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}


class SalesforceOAuth2(object):

    def __init__(self, client_id, client_secret, callback_url, sandbox):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url
        if sandbox:
            self.auth_site = 'https://test.salesforce.com'
        else:
            self.auth_site = 'https://login.salesforce.com'
        self.json = None

    def _request_token(self, request_data):
        url = self.auth_site + '/services/oauth2/token'
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        data.update(request_data)
        response = requests.post(url, headers=HTTP_HEADERS, data=data)
        response.raise_for_status()
        self.json = response.json()
        return response.json()

    def get_authorize_url(self, scope):
        url = self.auth_site + '/services/oauth2/authorize'
        url += '?response_type=code'
        url += '&client_id={}'.format(self.client_id)
        url += '&redirect_uri={}'.format(self.callback_url)
        url += '&scope={}'.format(quote(scope))
        return url

    def get_token(self, code):
        data = {
            'grant_type': 'authorization_code',
            'redirect_uri': self.callback_url,
            'code': code,
        }
        return self._request_token(data)

    def refresh_token(self):
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
        }
        return self._request_token(data)

    def revoke_token(self, current_token):
        url = self.auth_site + '/services/oauth2/revoke'
        data = {'token': quote(current_token)}
        response = requests.post(url, headers=HTTP_HEADERS, data=data)
        response.raise_for_status()
        return response.json()


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    parent = None

    def do_GET(self):
        args = parse_qs(urlparse(self.path).query, keep_blank_values=True)
        self.parent.response = self.parent.oauth_api.get_token(args['code'])
        self.send_response(httplib.OK)
        self.end_headers()
        self.wfile.write('OK')


class CaptureSalesforceOAuth(object):

    def __init__(self, client_id, client_secret, callback_url, sandbox, scope):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url
        self.sandbox = sandbox
        self.httpd = None
        self.oauth_api = self._get_oauth_api()
        self.response = None
        self.scope = scope
        self.httpd_timeout = 300

    def __call__(self):
        url = self.oauth_api.get_authorize_url(self.scope)
        self._launch_browser(url)
        self._create_httpd()
        self.httpd.handle_request()
        return self.response

    def _create_httpd(self):
        url_parts = urlparse(self.callback_url)
        server_address = (url_parts.hostname, url_parts.port)
        OAuthCallbackHandler.parent = self
        self.httpd = HTTPServer(server_address, OAuthCallbackHandler)
        self.httpd.timeout = self.httpd_timeout

    def _get_oauth_api(self):
        return SalesforceOAuth2(
            self.client_id,
            self.client_secret,
            self.callback_url,
            self.sandbox,
        )

    def _launch_browser(self, url):
        webbrowser.open(url, new=1)
