import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Type

from cumulusci.core.config import BaseProjectConfig, ServiceConfig
from cumulusci.core.dependencies.base import DynamicDependency
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.release_notes.generator import BaseReleaseNotesGenerator
from cumulusci.utils.classutils import get_all_subclasses
from cumulusci.vcs.models import AbstractRelease, AbstractRepo
from cumulusci.vcs.utils import AbstractCommitDir


class VCSService(ABC):
    """This is an abstract base class for VCS services.
    It defines the interface that all VCS services must implement.
    Subclasses should provide their own implementations of the methods and properties defined here.
    """

    logger: logging.Logger
    config: BaseProjectConfig
    service_config: ServiceConfig
    name: str
    keychain: Optional[BaseProjectKeychain]
    _service_registry: List["VCSService"] = []

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
        self.service_config = config.keychain.get_service(self.service_type, name)
        self.name = self.service_config.name or name
        self.keychain = config.keychain
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

    @property
    @abstractmethod
    def dynamic_dependency_class(self) -> Type[DynamicDependency]:
        """Returns the dynamic dependency class for the VCS service.
        This property should be overridden by subclasses to provide
        the specific dynamic dependency class. For example, it could
        return "GitHubDynamicDependency", "BitbucketDynamicDependency", etc."""
        raise NotImplementedError(
            "Subclasses should define the dynamic_dependency_class property"
        )

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

    @classmethod
    @abstractmethod
    def get_service_for_url(
        cls, project_config: BaseProjectConfig, url: str, service_alias: str = None
    ) -> Optional["VCSService"]:
        """Returns the service configuration for the given URL.
        This method should be overridden by subclasses to provide
        specific logic for retrieving the service configuration.
        The method should raise an exception if the validation fails."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @classmethod
    def registered_services(cls) -> List[Type["VCSService"]]:
        """This method returns all subclasses of VCSService that have been registered.
        It can be used to dynamically discover available VCS services."""
        return get_all_subclasses(cls)

    @abstractmethod
    def get_repository(self, options: dict = {}) -> AbstractRepo:
        """Returns the repository object for the VCS service.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the repository.
        The method should return an instance of a class that implements
        the AbstractRepo interface."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def parse_repo_url(self) -> List[str]:
        """Returns the owner, repo_name, and host from the repository URL.
        This method should be overridden by subclasses to provide
        the specific implementation for parsing the repository URL.
        The method should return a list containing the owner, repo_name, and host."""
        raise NotImplementedError(
            "Subclasses should provide their own implementation of parse_repo_url"
        )

    @abstractmethod
    def get_committer(self, repo: AbstractRepo) -> AbstractCommitDir:
        """Returns the committer for the VCS repository."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def markdown(
        self, release: AbstractRelease, mode: str = "", context: str = ""
    ) -> str:
        """Returns the markdown for the release.
        This method should be overridden by subclasses to provide
        the specific implementation for retrieving the markdown.
        The method should return a string containing the markdown."""
        raise NotImplementedError("Subclasses should provide their own implementation")

    @abstractmethod
    def release_notes_generator(self, options: dict) -> BaseReleaseNotesGenerator:
        """Returns the release notes generator for the VCS service."""
        raise NotImplementedError(
            "Subclasses should define the release_notes_generator property"
        )

    @abstractmethod
    def parent_pr_notes_generator(
        self, repo: AbstractRepo
    ) -> BaseReleaseNotesGenerator:
        """Returns the parent PR notes generator for the VCS service."""
        raise NotImplementedError(
            "Subclasses should define the parent_pr_notes_generator property"
        )
