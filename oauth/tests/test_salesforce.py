import httplib
import threading
import time
import unittest
import urllib2
from Queue import Queue

import mock
import responses

from oauth.salesforce import CaptureSalesforceOAuth


@mock.patch('webbrowser.open', mock.MagicMock(return_value=None))
class TestCaptureSalesforceOAuth(unittest.TestCase):

    @responses.activate
    def test_oauth_flow(self):
        client_id = 'foo_id'
        client_secret = 'foo_secret'
        callback_url = 'http://localhost:8080'
        sandbox = False
        scope = 'refresh_token web full'

        # mock response for SalesforceOAuth2.get_token()
        expected_response = {
            u'access_token': u'abc123',
            u'id_token': u'abc123',
            u'token_type': u'Bearer',
            u'signature': u'abc123',
            u'issued_at': u'12345',
            u'scope': u'{}'.format(scope),
            u'instance_url': u'https://na15.salesforce.com',
            u'id': u'https://login.salesforce.com/id/abc/xyz',
            u'refresh_token': u'abc123',
        }
        responses.add(
            responses.POST,
            'https://login.salesforce.com/services/oauth2/token',
            status=httplib.OK,
            json=expected_response,
        )

        # create CaptureSalesforceOAuth instance
        o = CaptureSalesforceOAuth(
            client_id,
            client_secret,
            callback_url,
            sandbox,
            scope,
        )

        # call OAuth object on another thread - this spawns local httpd
        t = threading.Thread(target=o.__call__)
        t.start()
        while True:
            if o.httpd:
                break
            print 'waiting for o.httpd'
            time.sleep(0.01)

        # simulate callback from browser
        response = urllib2.urlopen(callback_url + '?code=123')

        # wait for thread to complete
        t.join()

        # verify
        self.assertEqual(o.response, expected_response)
        self.assertEqual(response.read(), 'OK')


if __name__ == '__main__':
    unittest.main()
