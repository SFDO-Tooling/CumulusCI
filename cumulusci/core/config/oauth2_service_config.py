from abc import ABC
from abc import abstractmethod
from typing import Dict

from cumulusci.core.config import ServiceConfig


class OAuth2ServiceConfig(ServiceConfig, ABC):
    """Base class for services that require and OAuth2 Client
    for establishing a connection."""

    @abstractmethod
    def connect(self) -> Dict:
        """This method is called when the service is first connected
        via `cci service connect`. This method should perform the necessary
        OAuth flow and return a dict of values that the service would like
        stored in the services `config` dict."""
        raise NotImplementedError()
