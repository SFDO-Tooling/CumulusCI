from abc import ABC, abstractclassmethod
from typing import Dict

from cumulusci.core.config import ServiceConfig


class OAuth2ServiceConfig(ServiceConfig, ABC):
    """Base class for services that require an OAuth2 Client
    for establishing a connection."""

    @abstractclassmethod
    def connect(self) -> Dict:
        """This method is called when the service is first connected
        via `cci service connect`. This method should perform the necessary
        OAuth flow and return a dict of values that the service would like
        stored in the services `config` dict."""
        raise NotImplementedError
