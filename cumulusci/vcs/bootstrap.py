import logging
from typing import Optional

from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.utils import import_global
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.models import AbstractGitTag, AbstractRef, AbstractRepo


def get_service(
    config: BaseProjectConfig, logger: Optional[logging.Logger] = None
) -> VCSService:
    """Gets the VCS service based on the configuration.
    This function retrieves the VCS service type based on the CumulusCI
    configuration provided.
    If the service type is not specified in the configuration, it defaults to "github".
    The VCS Service class is expected to be defined in the configuration
    under the "class_path" key. If the class path is not found, a CumulusCIException is raised.

    Args:
        config (BaseProjectConfig): The configuration dictionary for the VCS service.

    Raises:
        CumulusCIException: Raised when the provider class is not found in the config.

    Returns:
        VCSService: The VCS service provider class.
    """
    service_type: str = config.lookup("project__service_type") or "github"

    provider_klass = None
    provider_path: str = config.services[service_type].get("class_path", None)

    if provider_path is not None:
        try:
            provider_klass = import_global(provider_path)
        except ImportError as e:
            raise CumulusCIException(
                f"Failed to import provider class from path '{provider_path}': {e}"
            )
    else:
        raise CumulusCIException(
            f"Provider class for {service_type} not found in config"
        )

    if issubclass(provider_klass, VCSService):
        vcs_service: VCSService = provider_klass(config, logger=logger)

        return vcs_service

    raise CumulusCIException(
        f"Provider class for {provider_path} is not a subclass of VCSService"
    )


def get_ref_for_tag(repo: AbstractRepo, tag_name: str) -> AbstractRef:
    """Gets a Reference object for the tag with the given name"""
    return repo.get_ref_for_tag(tag_name)


def get_tag_by_name(repo: AbstractRepo, tag_name: str) -> AbstractGitTag:
    """Fetches a tag by name from the given repository"""
    ref: AbstractRef = get_ref_for_tag(repo, tag_name)
    return repo.get_tag_by_ref(ref, tag_name)
