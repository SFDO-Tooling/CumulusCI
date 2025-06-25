from json import JSONDecodeError
from unittest.mock import Mock

import pytest

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


@pytest.fixture
def mock_http_response():
    def _mock_response(status=200, content_type="application/json", body=""):
        response = Mock()
        response.status_code = status
        response.headers = {"Content-Type": content_type}
        response.text = body
        # For simple-salesforce, the raw response's reason attribute might be accessed
        response.raw = Mock()
        response.raw.reason = "OK"

        def json_func():
            import json

            if not body:
                raise JSONDecodeError("Expecting value", "", 0)
            return json.loads(body)

        response.json = json_func
        return response

    return _mock_response


def test_sf_api_retries(mock_http_response):
    """
    Tests that the simple_salesforce connection correctly retries on specific network errors.
    """
    org_config = Mock()
    proj_config = Mock()
    service_mock = Mock()

    service_mock.client_id = "TEST_CLIENT_ID"
    proj_config.keychain.get_service.return_value = service_mock
    org_config.instance_url = "https://your-instance.my.salesforce.com"
    org_config.access_token = "dummy_access_token"

    sf = get_simple_salesforce_connection(proj_config, org_config, api_version="58.0")

    adapter = sf.session.get_adapter(org_config.instance_url)

    assert adapter.max_retries.backoff_factor == 0.3
    assert 502 in adapter.max_retries.status_forcelist
