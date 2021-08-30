import responses

from cumulusci.core.config import ServiceConfig
from cumulusci.core.config.marketing_cloud_service_config import (
    MarketingCloudServiceConfig,
)
from cumulusci.tests.util import create_project_config

from ..api import MarketingCloudDeploySubscriberAttribute

EXPECTED_SOAP_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
    xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
    xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <env:Header xmlns:env="http://www.w3.org/2003/05/soap-envelope">
        <wsa:Action>ConfigureResponse</wsa:Action>
        <wsa:MessageID>urn:uuid:9be492dc-a0b9-4cf9-908b-e02a11d623c3</wsa:MessageID>
        <wsa:RelatesTo>urn:uuid:b7df082c-4ddb-4a62-8cda-de290f42b9c0</wsa:RelatesTo>
        <wsa:To>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:To>
        <wsse:Security>
            <wsu:Timestamp wsu:Id="Timestamp-61ba3507-784d-4084-bdf0-0ca052fc29ec">
                <wsu:Created>2021-08-30T19:24:48Z</wsu:Created>
                <wsu:Expires>2021-08-30T19:29:48Z</wsu:Expires>
            </wsu:Timestamp>
        </wsse:Security>
    </env:Header>
    <soap:Body>
        <ConfigureResponseMsg xmlns="http://exacttarget.com/wsdl/partnerAPI">
            <Results>
                <Result>
                    <StatusCode>OK</StatusCode>
                    <StatusMessage>Success</StatusMessage>
                    <OrdinalID>0</OrdinalID>
                    <Object xsi:type="PropertyDefinition">
                        <PartnerKey xsi:nil="true" />
                        <ID>126713</ID>
                        <ObjectID xsi:nil="true" />
                        <Name>test</Name>
                        <PropertyType>string</PropertyType>
                    </Object>
                </Result>
            </Results>
            <OverallStatus>OK</OverallStatus>
            <OverallStatusMessage />
            <RequestID>ef959dde-a21d-46ac-b2de-98d9e656ed6f</RequestID>
        </ConfigureResponseMsg>
    </soap:Body>
</soap:Envelope>"""


@responses.activate
def test_deploy_marketing_cloud_subscriber_attribute_task(create_task):
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

    responses.add(
        "POST",
        "https://tssd.auth.marketingcloudapis.com/v2/token",
        json={"access_token": "ACCESS_TOKEN"},
    )
    responses.add(
        "POST",
        "https://tssd.soap.marketingcloudapis.com/Service.asmx",
        body=EXPECTED_SOAP_RESPONSE,
    )

    task = create_task(
        MarketingCloudDeploySubscriberAttribute,
        {
            "attribute_name": "test",
        },
        project_config=project_config,
    )
    task()
