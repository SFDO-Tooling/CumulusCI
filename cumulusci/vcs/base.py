import logging
from abc import ABC, abstractmethod
from typing import Optional

from cumulusci.core.config import BaseProjectConfig, ServiceConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.vcs.models import AbstractRepo


class VCSService(ABC):
    """This is an abstract base class for VCS services.
    It defines the interface that all VCS services must implement.
    Subclasses should provide their own implementations of the methods and properties defined here.
    """

    logger: logging.Logger
    config: BaseProjectConfig

    def __init__(
        self, config: BaseProjectConfig, name: Optional[str] = None, **kwargs
    ) -> None:
        """Initializes the VCS service with the given configuration, service name, and keychain.

        Args:
            config (BaseProjectConfig): The configuration for the GitHub service.
            name (str): Optional: The name or alias of the VCS service.
            **kwargs: Additional keyword arguments.
        """
        self.config = config
        self.service_config: ServiceConfig = config.keychain.get_service(
            self.service_type, name
        )
        self.name: str = self.service_config.name
        self.keychain: Optional["BaseProjectKeychain"] = config.keychain
        self.logger = kwargs.get("logger") or logging.getLogger(__name__)

    @property
    def service_type(self) -> str:
        """Returns the service type of the VCS service.
        This property should be overridden by subclasses to provide
        the specific service type. For example, it could return "github",
        "bitbucket", etc. The service type is used to identify the
        specific VCS service being used."""
        if isinstance(self.__class__.service_type, property):
            raise NotImplementedError(
                "Subclasses should define the service_type property"
            )
        return self.__class__.service_type

    @classmethod
    @abstractmethod
    def validate_service(cls, options: dict, keychain) -> dict:
        """Validate the service configuration.
        This method should be overridden by subclasses to provide
        specific validation logic. For example, it could check if the
        required options are present, valid values and able to
        establish a connection with the VCS.
        The method should raise an exception if the validation fails."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def get_repository(self) -> AbstractRepo:
        """Returns the repository object for the VCS service.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the repository.
        The method should return an instance of a class that implements
        the AbstractRepo interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")
