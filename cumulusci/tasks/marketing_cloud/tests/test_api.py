import responses

from cumulusci.tasks.marketing_cloud.tests import test_api_soap_envelopes as envelopes

from ..api import CreateSubscriberAttribute, CreateUser, UpdateUserRole
from ..mc_constants import MC_API_VERSION


@responses.activate
def test_marketing_cloud_create_subscriber_attribute_task(
    create_task, mc_project_config
):
    responses.add(
        "POST",
        f"https://tssd.auth.marketingcloudapis.com/{MC_API_VERSION}/token",
        json={"access_token": "ACCESS_TOKEN"},
    )
    responses.add(
        "POST",
        "https://tssd.soap.marketingcloudapis.com/Service.asmx",
        body=envelopes.CREATE_SUBSCRIBER_ATTRIBUTE_EXPECTED_SOAP_RESPONSE,
    )

    task = create_task(
        CreateSubscriberAttribute,
        {
            "attribute_name": "Test Subscriber Attribute",
        },
        project_config=mc_project_config,
    )
    task()
    assert task.return_values == {"success": True}


@responses.activate
def test_marketing_cloud_create_user_task(create_task, mc_project_config):
    responses.add(
        "POST",
        f"https://tssd.auth.marketingcloudapis.com/{MC_API_VERSION}/token",
        json={"access_token": "ACCESS_TOKEN"},
    )
    responses.add(
        "POST",
        "https://tssd.soap.marketingcloudapis.com/Service.asmx",
        body=envelopes.CREATE_USER_EXPECTED_SOAP_RESPONSE,
    )

    task = create_task(
        CreateUser,
        {
            "parent_bu_mid": "523005197",
            "default_bu_mid": "523008403",
            "external_key": "Don_Draper_Key_1926",
            "user_name": "Don Draper",
            "user_email": "don.draper@sterlingcooper.com",
            "user_password": "SterlingCooperDraperPryce1!",
            "user_username": "sterling-don",
            "role_id": "31",
            "activate_if_existing": "True",
        },
        project_config=mc_project_config,
    )
    task()
    assert task.return_values == {"success": True}

    request = responses.calls[-1].request
    assert b"<ActiveFlag>true</ActiveFlag>" in request.body
    assert b"<IsLocked>false</IsLocked>" in request.body


@responses.activate
def test_marketing_cloud_update_user_role_task(create_task, mc_project_config):
    responses.add(
        "POST",
        f"https://tssd.auth.marketingcloudapis.com/{MC_API_VERSION}/token",
        json={"access_token": "ACCESS_TOKEN"},
    )
    responses.add(
        "POST",
        "https://tssd.soap.marketingcloudapis.com/Service.asmx",
        body=envelopes.UPDATE_USER_ROLE_EXPECTED_SOAP_RESPONSE,
    )

    task = create_task(
        UpdateUserRole,
        {
            "account_mid": "523005197",
            "external_key": "Don_Draper_Key_1926",
            "user_name": "Partner Don Draper",
            "user_email": "don.draper@sterlingcooper.com",
            "user_password": "SterlingCooperDraperPryce1!",
            "role_id": "31",
        },
        project_config=mc_project_config,
    )
    task()
    assert task.return_values == {"success": True}
