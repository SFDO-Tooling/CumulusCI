import logging
import re
from typing import Optional

from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.utils import import_global
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.models import (
    AbstractGitTag,
    AbstractRef,
    AbstractRepo,
    AbstractRepoCommit,
)


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


VERSION_ID_RE: re.Pattern[str] = re.compile(r"version_id: (\S+)")


def get_version_id_from_commit(
    repo: AbstractRepo, commit_sha: str, context: str
) -> Optional[str]:
    """Fetches the version ID from a commit status"""
    commit = get_commit(repo, commit_sha)
    version_id = commit.get_statuses(context, regex_match=VERSION_ID_RE)
    return version_id


def get_commit(repo: AbstractRepo, commit_sha: str) -> Optional[AbstractRepoCommit]:
    """Given a SHA1 hash, retrieve a AbstractRepoCommit object."""
    return repo.get_commit(commit_sha)
