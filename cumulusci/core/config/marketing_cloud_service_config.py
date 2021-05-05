from cumulusci.core.config import ServiceConfig
from cumulusci.oauth.client import OAuth2Client
from cumulusci.oauth.client_info import OAuthClientInfo


class MarketingCloudServiceConfig(ServiceConfig):
    def __init__(self, config, keychain):
        super().__init__(config=config)
        self._client_info = keychain.get_service("oauth-client", config["oauth_client"])

    def connect(client_info: OAuthClientInfo):
        oauth_client = OAuth2Client(client_info)
        return oauth_client.auth_code_flow(use_https=True)

    @property
    def access_token(self):
        return self._refresh_token()

    def _refresh_token(self):
        """Gets a fresh access token for the user.
        This will prompt the user to login to their MC account.

        The info dict passed back from the OAuth flow includes:
        * access_token
        * refresh_token
        """
        oauth_client = OAuth2Client(self._client_info)
        info = oauth_client.refresh_token(self.refresh_token)
        return info["access_token"]
