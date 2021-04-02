from json import JSONDecodeError
from unittest.mock import Mock, patch

from cumulusci import __version__
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection


def test_connection():
    org_config = OrgConfig(
        {
            "instance_url": "https://orgname.my.salesforce.com",
            "access_token": "BOGUS",
        },
        "test",
    )
    proj_config = Mock()
    service_mock = Mock()
    service_mock.client_id = "TEST"
    proj_config.keychain.get_service.return_value = service_mock
    proj_config.project__package__api_version = "51.0"

    sf = get_simple_salesforce_connection(proj_config, org_config)
    assert sf.base_url == "https://orgname.my.salesforce.com/services/data/v51.0/"
    assert sf.headers["Authorization"] == "Bearer BOGUS"
    assert sf.headers["Sforce-Call-Options"] == "client=TEST"


def test_connection__explicit_api_version():
    org_config = OrgConfig(
        {
            "instance_url": "https://orgname.my.salesforce.com",
            "access_token": "BOGUS",
        },
        "test",
    )
    proj_config = Mock()
    service_mock = Mock()
    service_mock.client_id = "TEST"
    proj_config.keychain.get_service.return_value = service_mock

    sf = get_simple_salesforce_connection(proj_config, org_config, api_version="42.0")
    assert sf.base_url == "https://orgname.my.salesforce.com/services/data/v42.0/"


def test_connection__no_connected_app():
    org_config = OrgConfig(
        {
            "instance_url": "https://orgname.my.salesforce.com",
            "access_token": "BOGUS",
        },
        "test",
    )
    proj_config = Mock()
    proj_config.keychain.get_service.side_effect = ServiceNotConfigured

    sf = get_simple_salesforce_connection(proj_config, org_config)
    assert sf.headers["Sforce-Call-Options"] == f"client=CumulusCI/{__version__}"


def test_connection__with_port():
    org_config = OrgConfig(
        {
            "instance_url": "https://orgname.my.salesforce.com:8080",
            "access_token": "BOGUS",
        },
        "test",
    )
    proj_config = Mock()
    service_mock = Mock()
    service_mock.client_id = "TEST"
    proj_config.keychain.get_service.return_value = service_mock
    proj_config.project__package__api_version = "51.0"

    sf = get_simple_salesforce_connection(proj_config, org_config)
    assert sf.base_url == "https://orgname.my.salesforce.com:8080/services/data/v51.0/"


def test_sf_api_retries(mock_http_response):
    org_config = Mock()
    proj_config = Mock()
    service_mock = Mock()
    service_mock.client_id = "TEST"
    proj_config.keychain.get_service.return_value = service_mock
    org_config.instance_url = "https://enterprise-dream-6536.cs41.my.salesforce.com"
    org_config.access_token = "httpsenterprise-dream-6536.cs41.my.salesforce.com"

    sf = get_simple_salesforce_connection(proj_config, org_config, api_version="42.0")
    adapter = sf.session.get_adapter("http://")

    assert 0.3 == adapter.max_retries.backoff_factor
    assert 502 in adapter.max_retries.status_forcelist

    with patch(
        "urllib3.connectionpool.HTTPConnectionPool._make_request"
    ) as _make_request:
        _make_request.side_effect = [
            ConnectionResetError,
            mock_http_response(status=200),
        ]

        try:
            sf.describe()
        except JSONDecodeError:
            # We're not returning a message to decode
            pass

        assert 2 == _make_request.call_count
