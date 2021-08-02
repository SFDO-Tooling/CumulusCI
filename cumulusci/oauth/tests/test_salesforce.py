from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import SalesforceCredentialsException
from cumulusci.oauth.salesforce import jwt_session


@responses.activate
@mock.patch("cumulusci.oauth.salesforce.jwt.encode")
def test_jwt_session(encode):
    # Mock the call to encode so we don't need
    # to generate a private key that would be committed
    error = "Yeti"
    responses.add(
        responses.POST,
        "https://login.salesforce.com/services/oauth2/token",
        body=error,
        status=400,
    )
    with pytest.raises(
        SalesforceCredentialsException, match=f"Error retrieving access token: {error}"
    ):
        jwt_session("client_id", "server_key", "username")


@mock.patch("cumulusci.oauth.salesforce.jwt.encode")
def test_jwt_session__enhanced_domains_enabled(encode):
    # raise an assertion error if the registered url was not accessed
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.POST,
            "https://test.salesforce.com/services/oauth2/token",
            body='{"message":"well done mate!"}',
            status=200,
        )
        jwt_session(
            "client_id",
            "server_key",
            "username",
            url="https://supercool.sandbox.my.salesforce.com",
        )
