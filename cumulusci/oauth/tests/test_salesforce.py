from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import http.client
import threading
import time
import unittest
import urllib.request, urllib.error, urllib.parse

import mock
import responses

from cumulusci.oauth.salesforce import CaptureSalesforceOAuth
from cumulusci.oauth.exceptions import SalesforceOAuthError


@mock.patch('webbrowser.open', mock.MagicMock(return_value=None))
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
        self.client_id = 'foo_id'
        self.client_secret = 'foo_secret'
        self.callback_url = 'http://localhost:8080'
        self.scope = 'refresh_token web full'
        self.auth_site = 'https://login.salesforce.com'

    @responses.activate
    def test_oauth_flow(self):

        # mock response to URL validation
        responses.add(
            responses.GET,
            'https://login.salesforce.com/services/oauth2/authorize',
            status=http.client.OK,
        )

        # mock response for SalesforceOAuth2.get_token()
        expected_response = {
            u'access_token': u'abc123',
            u'id_token': u'abc123',
            u'token_type': u'Bearer',
            u'signature': u'abc123',
            u'issued_at': u'12345',
            u'scope': u'{}'.format(self.scope),
            u'instance_url': u'https://na15.salesforce.com',
            u'id': u'https://login.salesforce.com/id/abc/xyz',
            u'refresh_token': u'abc123',
        }
        responses.add(
            responses.POST,
            'https://login.salesforce.com/services/oauth2/token',
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
            print('waiting for o.httpd')
            time.sleep(0.01)

        # simulate callback from browser
        response = urllib.request.urlopen(self.callback_url + '?code=123')

        # wait for thread to complete
        t.join()

        # verify
        self.assertEqual(o.response.json(), expected_response)
        self.assertEqual(response.read(), b'OK')

    @responses.activate
    def test_bad_request(self):

        # mock response to URL validation
        responses.add(
            responses.GET,
            'https://login.salesforce.com/services/oauth2/authorize',
            status=http.client.BAD_REQUEST,
        )

        # create CaptureSalesforceOAuth instance
        o = self._create_oauth()

        # call OAuth object with bad info
        with self.assertRaises(SalesforceOAuthError):
            o()


if __name__ == '__main__':
    unittest.main()
