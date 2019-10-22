import io
import unittest

from http.client import HTTPMessage
from json import JSONDecodeError
from unittest.mock import Mock, patch

from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci import __version__


class MockHttpResponse(Mock):
    def __init__(self, status, msg=None):
        super(MockHttpResponse, self).__init__()
        self.status = status
        self.strict = 0
        self.version = 0
        self.reason = None
        self.msg = HTTPMessage(io.BytesIO())
        self.closed = True

    def read(self):
        return b""

    def isclosed(self):
        return self.closed


class TestSalesforceApiUtils(unittest.TestCase):
    @patch("simple_salesforce.Salesforce")
    def test_connection(self, mock_sf):
        org_config = Mock()
        proj_config = Mock()
        service_mock = Mock()
        service_mock.client_id = "TEST"
        proj_config.keychain.get_service.return_value = service_mock

        get_simple_salesforce_connection(proj_config, org_config)
        mock_sf.assert_called_once_with(
            instance_url=org_config.instance_url,
            session_id=org_config.access_token,
            version=proj_config.project__package__api_version,
        )

        mock_sf.return_value.headers.setdefault.assert_called_once_with(
            "Sforce-Call-Options", "client={}".format(service_mock.client_id)
        )

    @patch("simple_salesforce.Salesforce")
    def test_connection__explicit_api_version(self, mock_sf):
        org_config = Mock()
        proj_config = Mock()
        service_mock = Mock()
        service_mock.client_id = "TEST"
        proj_config.keychain.get_service.return_value = service_mock

        get_simple_salesforce_connection(proj_config, org_config, api_version="42.0")
        mock_sf.assert_called_once_with(
            instance_url=org_config.instance_url,
            session_id=org_config.access_token,
            version="42.0",
        )

        mock_sf.return_value.headers.setdefault.assert_called_once_with(
            "Sforce-Call-Options", "client={}".format(service_mock.client_id)
        )

    @patch("simple_salesforce.Salesforce")
    def test_connection__no_connected_app(self, mock_sf):
        org_config = Mock()
        proj_config = Mock()
        proj_config.keychain.get_service.side_effect = ServiceNotConfigured

        get_simple_salesforce_connection(proj_config, org_config)

        mock_sf.return_value.headers.setdefault.assert_called_once_with(
            "Sforce-Call-Options",
            "client={}".format("CumulusCI/{}".format(__version__)),
        )

    @patch("urllib3.connectionpool.HTTPConnectionPool._make_request")
    def test_sf_api_retries(self, _make_request):
        org_config = Mock()
        proj_config = Mock()
        service_mock = Mock()
        service_mock.client_id = "TEST"
        proj_config.keychain.get_service.return_value = service_mock
        org_config.instance_url = "https://enterprise-dream-6536.cs41.my.salesforce.com"
        org_config.access_token = "httpsenterprise-dream-6536.cs41.my.salesforce.com"

        sf = get_simple_salesforce_connection(
            proj_config, org_config, api_version="42.0"
        )
        adapter = sf.session.get_adapter("http://")

        assert 0.3 == adapter.max_retries.backoff_factor
        assert 502 in adapter.max_retries.status_forcelist

        _make_request.side_effect = [
            MockHttpResponse(status=503),
            MockHttpResponse(status=200),
        ]

        try:
            sf.describe()
        except JSONDecodeError:
            # We're not returning a message to decode
            pass

        assert 2 == _make_request.call_count
