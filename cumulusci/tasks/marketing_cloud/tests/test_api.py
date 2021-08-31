import pytest
import responses

from cumulusci.core.config import ServiceConfig
from cumulusci.core.config.marketing_cloud_service_config import (
    MarketingCloudServiceConfig,
)
from cumulusci.tasks.marketing_cloud.tests import test_api_soap_envelopes as envelopes
from cumulusci.tests.util import create_project_config

from ..api import MarketingCloudCreateSubscriberAttribute


@pytest.fixture
def project_config():
    project_config = create_project_config()
    project_config.keychain.set_service(
        "oauth2_client",
        "test",
        ServiceConfig(
            {
                "client_id": "MC_CLIENT_ID",
                "client_secret": "BOGUS",
                "auth_uri": "https://TSSD.auth.marketingcloudapis.com/v2/authorize",
                "token_uri": "https://TSSD.auth.marketingcloudapis.com/v2/token",
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
                "soap_instance_url": "https://TSSD.soap.marketingcloudapis.com/",
            },
            "test",
            project_config.keychain,
        ),
        False,
    )
    return project_config


@responses.activate
def test_marketing_cloud_create_subscriber_attribute_task(create_task, project_config):
    responses.add(
        "POST",
        "https://tssd.auth.marketingcloudapis.com/v2/token",
        json={"access_token": "ACCESS_TOKEN"},
    )
    responses.add(
        "POST",
        "https://tssd.soap.marketingcloudapis.com/Service.asmx",
        body=envelopes.CREATE_SUBSCRIBER_ATTRIBUTE_EXPECTED_SOAP_RESPONSE,
    )

    task = create_task(
        MarketingCloudCreateSubscriberAttribute,
        {
            "attribute_name": "test",
        },
        project_config=project_config,
    )
    task()
