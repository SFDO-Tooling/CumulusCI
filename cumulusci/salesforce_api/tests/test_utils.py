import unittest
from mock import Mock, patch
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci import __version__


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
