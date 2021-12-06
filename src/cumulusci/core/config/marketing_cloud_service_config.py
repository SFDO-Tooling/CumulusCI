from typing import Dict
from urllib.parse import urlparse

from cumulusci.core.config.oauth2_service_config import OAuth2ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.oauth.client import OAuth2Client


class MarketingCloudServiceConfig(OAuth2ServiceConfig):
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
