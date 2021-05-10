from typing import Dict

from cumulusci.core.config.oauth2_service_config import OAuth2ServiceConfig
from cumulusci.core.keychain import EncryptedFileProjectKeychain
from cumulusci.oauth.client import OAuth2Client


class MarketingCloudServiceConfig(OAuth2ServiceConfig):
    def __init__(self, config, keychain):
        super().__init__(config=config)
        self._client_config = keychain.get_service(
            "oauth2_client", config["oauth2_client"]
        )

    def connect(keychain: EncryptedFileProjectKeychain, kwargs: Dict):
        """This is called when a service is connected via `cci service connect`

        @param keychain - A keychain for accessing services
        @param kwargs - Any keyword arguments passed to `cci service connect`
        """
        client_config = keychain.get_service("oauth2_client", kwargs["oauth2_client"])
        oauth_client = OAuth2Client(client_config.config)
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
        oauth_client = OAuth2Client(self._client_config.config)
        info = oauth_client.refresh_token(self.refresh_token)
        return info["access_token"]
