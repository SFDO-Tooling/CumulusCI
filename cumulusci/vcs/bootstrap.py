import logging
import re
from typing import Optional

from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.utils import import_global
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.models import (
    AbstractGitTag,
    AbstractPullRequest,
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
    service_type, service_alias = config.get_project_service()

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
        vcs_service: VCSService = provider_klass(config, service_alias, logger=logger)

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
    commit: Optional[AbstractRepoCommit] = get_commit(repo, commit_sha)
    if commit is not None:
        version_id = commit.get_statuses(context, regex_match=VERSION_ID_RE)
        return version_id
    return None


def get_commit(repo: AbstractRepo, commit_sha: str) -> Optional[AbstractRepoCommit]:
    """Given a SHA1 hash, retrieve a AbstractRepoCommit object."""
    return repo.get_commit(commit_sha)


def get_service_for_url(
    config: BaseProjectConfig, url: str, options: dict = {}
) -> VCSService:
    """Gets the VCS service for a given URL."""
    class_services = {
        k: v for k, v in config.services.items() if v.get("class_path") is not None
    }

    for service_name, service_config in class_services.items():
        provider_path: str = service_config.get("class_path", None)
        provider_klass = None

        if provider_path is None:
            continue

        try:
            provider_klass = import_global(provider_path)
        except ImportError as e:
            raise CumulusCIException(
                f"Failed to import provider class from path '{provider_path}': {e}"
            )

        if hasattr(provider_klass, "get_service_for_url"):
            vcs_service: VCSService = provider_klass.get_service_for_url(
                config, url, options
            )
            return vcs_service
    raise CumulusCIException(f"Service for URL '{url}' not found.")


def get_pull_requests_with_base_branch(
    repo: AbstractRepo,
    base_branch_name: str,
    head: Optional[str] = None,
    state: Optional[str] = None,
) -> list:
    """Returns a list of pull requests with the given base branch"""
    if head:
        head = repo.owner_login + ":" + head
    return list(repo.pull_requests(base=base_branch_name, head=head, state=state))


def is_pull_request_merged(pull_request: AbstractPullRequest) -> bool:
    """Takes a AbstractPullRequest object"""
    return pull_request.merged_at is not None


def is_label_on_pull_request(
    repo: AbstractRepo, pull_request: AbstractPullRequest, label_name: str
) -> bool:
    """Returns True if the given label is on the pull request with the given
    pull request number. False otherwise."""
    labels = list(repo.get_pr_issue_labels(pull_request))

    return any(label_name == issue_label for issue_label in labels)
