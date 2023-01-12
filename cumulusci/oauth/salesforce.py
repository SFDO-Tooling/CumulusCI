import os
import re
from calendar import timegm
from datetime import datetime
from urllib.parse import urljoin

import jwt
import requests

from cumulusci.core.exceptions import SalesforceCredentialsException
from cumulusci.utils.http.requests_utils import safe_json_from_response

ENHANCED_DOMAIN_SUBSTRING = "sandbox.my.salesforce.com"
HTTP_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
SANDBOX_DOMAIN_RE = re.compile(
    r"^https://([\w\d-]+\.)?(test|cs\d+)(\.my)?\.salesforce\.com/?$"
)
SANDBOX_LOGIN_URL = (
    os.environ.get("SF_SANDBOX_LOGIN_URL") or "https://test.salesforce.com"
)
PROD_LOGIN_URL = os.environ.get("SF_PROD_LOGIN_URL") or "https://login.salesforce.com"


def jwt_session(
    client_id, private_key, username, url=None, auth_url=None, is_sandbox=False
):
    """Complete the JWT Token Oauth flow to obtain an access token for an org.

    :param client_id: Client Id for the connected app
    :param private_key: Private key used to sign the connected app's certificate
    :param username: Username to authenticate as
    :param url: Org's instance_url
    """
    if auth_url:
        aud = (
            SANDBOX_LOGIN_URL
            if auth_url.startswith(SANDBOX_LOGIN_URL)
            else PROD_LOGIN_URL
        )
    # check for enhanced domains (instanceless URLs)
    # https://developer.salesforce.com/docs/atlas.en-us.identityImplGuide.meta/identityImplGuide/domain_name_enhanced.htm
    elif url and ENHANCED_DOMAIN_SUBSTRING in url:
        url = aud = SANDBOX_LOGIN_URL
    else:
        aud = PROD_LOGIN_URL
        if url is None:
            url = PROD_LOGIN_URL
        else:
            m = SANDBOX_DOMAIN_RE.match(url)
            if m is not None:
                # sandbox
                aud = SANDBOX_LOGIN_URL
                # There can be a delay in syncing scratch org credentials
                # between instances, so let's use the specific one for this org.
                instance = m.group(2)
                url = f"https://{instance}.salesforce.com"

    if is_sandbox:  # pragma: no cover
        aud = SANDBOX_LOGIN_URL

    payload = {
        "alg": "RS256",
        "iss": client_id,
        "sub": username,
        "aud": aud,
        "exp": timegm(datetime.utcnow().utctimetuple()),
    }
    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": encoded_jwt,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_url = urljoin(url, "services/oauth2/token")
    response = requests.post(url=token_url, data=data, headers=headers)
    if response.status_code != 200:
        raise SalesforceCredentialsException(
            f"Error retrieving access token: {response.text}"
        )

    return safe_json_from_response(response)
