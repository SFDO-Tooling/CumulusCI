from typing import Dict

from cumulusci.core.config import ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.oauth.client import OAuth2Client


class OAuth2ServiceConfig(ServiceConfig):
    """Base class for services that require an OAuth2 Client
    for establishing a connection."""

    def __init__(self, config, service_type, name, keychain):
        super().__init__(config, name, keychain)
        self._service_type = service_type
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
        assert self._keychain, f"Keychain not set on {self.__class__.__name__}"
        self._keychain.set_service(self._service_type, self._name, self)
