import pytest

from cumulusci.core.config import ServiceConfig
from cumulusci.core.config.marketing_cloud_service_config import (
    MarketingCloudServiceConfig,
)
from cumulusci.tests.util import create_project_config

from ..mc_constants import MC_API_VERSION


@pytest.fixture
def mc_project_config():
    project_config = create_project_config()
    project_config.keychain.set_service(
        "oauth2_client",
        "test",
        ServiceConfig(
            {
                "client_id": "MC_CLIENT_ID",
                "client_secret": "BOGUS",
                "auth_uri": f"https://TSSD.auth.marketingcloudapis.com/{MC_API_VERSION}/authorize",
                "token_uri": f"https://TSSD.auth.marketingcloudapis.com/{MC_API_VERSION}/token",
                "callback_url": "https://127.0.0.1:8080/",
            },
            "test",
            project_config.keychain,
        ),
        False,
    )
    project_config.keychain.set_service(
        "marketing_cloud",
        "test",
        MarketingCloudServiceConfig(
            {
                "oauth2_client": "test",
                "refresh_token": "REFRESH",
                "rest_instance_url": "https://TSSD.auth.marketingcloudapis.com/",
                "soap_instance_url": "https://TSSD.soap.marketingcloudapis.com/",
            },
            "test",
            project_config.keychain,
        ),
        False,
    )
    return project_config
