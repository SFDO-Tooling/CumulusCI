import re

import pytest
import requests
import responses

from cumulusci.tasks.marketing_cloud.get_user_info import GetUserInfoTask
from cumulusci.tasks.marketing_cloud.mc_constants import MC_API_VERSION


@pytest.fixture
def get_user_info_task(create_task, mc_project_config):
    return create_task(GetUserInfoTask, {}, project_config=mc_project_config)


@pytest.fixture
def user_info_payload():
    return {
        "exp": 1527771992,
        "iss": "https://mc.exacttarget.com",
        "user": {
            "sub": "10654321",
            "name": "Auth_user_name",
            "preferred_username": "Auth_user_preferred_username",
            "email": "example@example.com",
            "locale": "en-GB",
            "zoneinfo": "Europe/London",
            "timezone": {
                "longName": "(GMT) Dublin, Edinburgh, Lisbon, London *",
                "shortName": "GMT+0",
                "offset": 0,
                "dst": True,
            },
        },
        "organization": {
            "member_id": 10123456,
            "enterprise_id": 10123456,
            "enterprise_name": "Auth_enterprise_name",
            "account_type": "enterprise",
            "stack_key": "S1",
            "region": "NA1",
            "locale": "en-US",
            "zoneinfo": "America/Los_Angeles",
            "timezone": {
                "longName": "(GMT-08:00) Pacific Time (US & Canada) *",
                "shortName": "GMT-8",
                "offset": -8,
                "dst": True,
            },
        },
        "rest": {
            "rest_instance_url": "https://mc563885gzs27c5t9-63k636ttgm.rest.marketingcloudapis.com",
            "soap_instance_url": "https://mc563885gzs27c5t9-63k636ttgm.soap.marketingcloudapis.com",
        },
        "application": {
            "id": "1a23b4cd-5e66-789f-0g1h-2i3a6efb6d80",
            "name": "auth_application_name",
            "redirectUrl": [
                "https://example.example.com*",
                "https://example.com/oauth-authorize",
                "https://example.example.com/***********",
            ],
            "appScopes": [
                "openid",
                "offline",
                "email_read",
                "email_send",
                "email_write",
            ],
        },
        "permissions": [
            {
                "objectTypeName": "Email",
                "operationName": "Update",
                "name": "Update",
                "id": 123,
            }
        ],
    }


@responses.activate
def test_get_user_info__success(get_user_info_task, user_info_payload):
    responses.add(
        "POST",
        "https://tssd.auth.marketingcloudapis.com/v2/token",
        json={"access_token": "ACCESS_TOKEN"},
    )
    responses.add(
        "GET",
        f"https://TSSD.auth.marketingcloudapis.com/{MC_API_VERSION}/userinfo",
        json=user_info_payload,
    )

    get_user_info_task()

    expected_payload = user_info_payload
    del expected_payload["rest"]
    del expected_payload["application"]
    del expected_payload["permissions"]

    assert get_user_info_task.return_values == expected_payload


@responses.activate
def test_get_user_info__HTTPError(get_user_info_task, user_info_payload):
    responses.add(
        "POST",
        "https://tssd.auth.marketingcloudapis.com/v2/token",
        json={"access_token": "ACCESS_TOKEN"},
    )
    responses.add(
        "GET",
        f"https://TSSD.auth.marketingcloudapis.com/{MC_API_VERSION}/userinfo",
        status=400,
        body="bad request",
    )
    with pytest.raises(
        requests.exceptions.HTTPError,
        match=re.escape(
            "400 Client Error: Bad Request for url: https://tssd.auth.marketingcloudapis.com/v2/userinfo"
        ),
    ):
        get_user_info_task()


def test_sanitize_payload(get_user_info_task):
    payload = {
        "foo": "foo-stuff",
        "bar": "bar-stuff",
        "rest": "rest-stuff",
        "application": "application-stuff",
        "permissions": "permission-stuff",
    }
    start_num_keys = len(payload.keys())
    sanitized_payload = get_user_info_task._sanitize_payload(payload)

    assert start_num_keys - 3 == len(sanitized_payload.keys())
    assert "rest" not in sanitized_payload
    assert "appliation" not in sanitized_payload
    assert "permissions" not in sanitized_payload
