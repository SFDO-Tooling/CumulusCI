import urllib.parse

import requests

from cumulusci.core.config import ServiceConfig
from cumulusci.core.config.marketing_cloud_service_config import (
    MarketingCloudServiceConfig,
)
from cumulusci.utils.http.requests_utils import safe_json_from_response

from .mc_constants import MC_API_VERSION


def get_mc_user_info(
    mc_oauth2_client_config: ServiceConfig, mc_config: MarketingCloudServiceConfig
) -> dict:
    """Make a call to the Marketing Cloud REST API UserInfo endpoint.
    Raises HTTPError for bad response status, otherwise returns the payload
    in full."""

    parsed = urllib.parse.urlparse(mc_oauth2_client_config.auth_uri)
    hostname_parts = parsed.hostname.split(".")
    hostname_parts[0] = mc_config.tssd
    url = parsed._replace(
        netloc=".".join(hostname_parts), path=f"/{MC_API_VERSION}/userinfo"
    )
    endpoint = urllib.parse.urlunparse(url)
    headers = {
        "Authorization": f"Bearer {mc_config.access_token}",
        "Content-Type": "application/json",
    }
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()

    return safe_json_from_response(response)
