from typing import Dict
from urllib.parse import urlparse

import requests

from cumulusci.core.config.oauth2_service_config import OAuth2ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.oauth.client import OAuth2Client
from cumulusci.utils.http.requests_utils import safe_json_from_response


class MarketingCloudServiceConfig(OAuth2ServiceConfig):

    refresh_token: str
    oauth2_client: str
    soap_instance_url: str
    rest_instance_url: str
    redirect_uri: str
    access_token: str

    def __init__(self, config, name, keychain):
        super().__init__(config, name, keychain)
        self._name = name
        self._keychain = keychain

    @classmethod
    def connect(cls, keychain: BaseProjectKeychain, kwargs: Dict):
        """This is called when a service is connected via `cci service connect`

        @param keychain - A keychain for accessing services
        @param kwargs - Any keyword arguments passed to `cci service connect`
        """
        client_config = keychain.get_service("oauth2_client", kwargs["oauth2_client"])
        config = client_config.config.copy()
        config["redirect_uri"] = config["callback_url"]
        oauth2_client = OAuth2Client(config)
        return oauth2_client.auth_code_flow()

    @property
    def tssd(self):
        """A dynamic value that represents the end user's subdomain.
        We can derive this value from either soap_instance_url or rest_instance_url
        which are present upon successful completion of an OAuth2 flow."""
        result = urlparse(self.config["rest_instance_url"])
        return result.netloc.split(".")[0]

    @property
    def access_token(self):
        return self._refresh_token()

    def _refresh_token(self):
        """Gets a fresh access token for the user.

        The info dict passed back from the OAuth flow includes:
        * access_token
        * refresh_token
        """
        oauth2_client_config = self._keychain.get_service(
            "oauth2_client", self.oauth2_client
        )
        oauth2_client = OAuth2Client(oauth2_client_config)
        info = oauth2_client.refresh_token(self.refresh_token)
        self.config.update(info)
        self.save()
        return info["access_token"]

    def save(self):
        assert self._keychain, "Keychain not set on MarketingCloudServiceConfig"
        self._keychain.set_service("marketing_cloud", self._name, self)

    def get_user_info(self) -> dict:
        """Make a call to the Marketing Cloud REST API UserInfo endpoint.
        Raises HTTPError for bad response status, otherwise returns the payload
        in full."""
        auth_uri = self.rest_instance_url.replace(".rest", ".auth")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        response = requests.get(f"{auth_uri}v2/userinfo", headers=headers)
        response.raise_for_status()

        return safe_json_from_response(response)
