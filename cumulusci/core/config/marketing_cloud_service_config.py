from typing import Dict

from cumulusci.core.config import ServiceConfig
from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.oauth.client import OAuth2Client


class MarketingCloudServiceConfig(ServiceConfig):
    def __init__(self, config, keychain):
        super().__init__(config=config)
        self._client_info = keychain.get_service("oauth-client", config["oauth_client"])

    def connect(keychain: EncryptedFileProjectKeychain, kwargs: Dict):
        """This method is called when a service is connected.

        @param keychain - A keychain for accessing services
        @param kwargs - Any keyword arguments passed to `cci service connect`
        """
        client_info = keychain.get_service("oauth-client", kwargs["oauth_client"])
        oauth_client = OAuth2Client(client_info)
        return oauth_client.auth_code_flow(use_https=True)

    @property
    def access_token(self):
        return self._refresh_token()

    def _refresh_token(self):
        """Gets a fresh access token for the user.

        The info dict passed back from the OAuth flow includes:
        * access_token
        * refresh_token
        """
        oauth_client = OAuth2Client(self._client_info)
        info = oauth_client.refresh_token(self.refresh_token)
        return info["access_token"]
