import requests

from cumulusci.utils.http.requests_utils import safe_json_from_response

from .mc_constants import MC_API_VERSION


def get_mc_user_info(tssd: str, access_token: str) -> dict:
    """Make a call to the Marketing Cloud REST API UserInfo endpoint.
    Raises HTTPError for bad response status, otherwise returns the payload
    in full."""
    endpoint = f"https://{tssd}.auth.marketingcloudapis.com/{MC_API_VERSION}/userinfo"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()

    return safe_json_from_response(response)


def get_mc_stack_key(tssd: str, access_token: str) -> str:
    """Return the stack_key associated with the given access token."""
    user_info_payload = get_mc_user_info(tssd, access_token)
    return user_info_payload["organization"]["stack_key"]
