from abc import ABC, abstractmethod

from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.vcs.models import AbstractRepo


class VCSService(ABC):
    """This is an abstract base class for VCS services.
    It defines the interface that all VCS services must implement.
    Subclasses should provide their own implementations of the methods and properties defined here.
    """

    def __init__(self, config: dict, name: str, keychain: BaseProjectKeychain):
        """Initializes the VCS service with the given configuration, service name, and keychain.

        Args:
            config (dict): The configuration dictionary for the VCS service, The service type options.
            name (str): The name or alias of the VCS service.
            keychain: The keychain object for managing credentials.
        """
        self.config = config
        self.name = name
        self.keychain = keychain

    @property
    def service_type(self):
        """Returns the type of the VCS service.
        This property should be defined by subclasses to provide
        the specific service type. For example, it could return "github",
        "bitbucket", etc. The service type is used to identify the
        specific VCS service being used."""

        if self._service_type is None:
            raise NotImplementedError(
                "Subclasses should provide their own implementation of service_type"
            )

        return self._service_type

    @service_type.setter
    @abstractmethod
    def service_type(self, value: str):
        """Sets the service type for the VCS service.

        Args:
            value (str): The type of the VCS service.
        """
        self._service_type = value

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
