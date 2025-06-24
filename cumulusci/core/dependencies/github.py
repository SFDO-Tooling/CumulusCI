import logging
from abc import ABC
from functools import lru_cache
from typing import Optional, Type

from pydantic import root_validator
from pydantic.networks import AnyUrl

import cumulusci.core.dependencies.base as base_dependency
from cumulusci.core.exceptions import DependencyResolutionError, GithubApiNotFoundError
from cumulusci.utils.git import split_repo_url
from cumulusci.vcs.github.adapter import GitHubRepository

logger = logging.getLogger(__name__)

VCS_GITHUB = "github"


@lru_cache(50)
def get_github_repo(project_config, url) -> GitHubRepository:
    from cumulusci.vcs.github.service import VCSService, get_github_service_for_url

    vcs_service: Optional[VCSService] = get_github_service_for_url(project_config, url)

    if vcs_service is None:
        raise DependencyResolutionError(
            f"Could not find a GitHub service for URL: {url}"
        )

    try:
        repo = vcs_service.get_repository(options={"repository_url": url})
        if repo is None:
            raise GithubApiNotFoundError(f"Get GitHub Repository found None. {url}")
        return repo
    except GithubApiNotFoundError as e:
        raise DependencyResolutionError(
            f"Could not find a GitHub repository at {url}: {e}"
        )


def _validate_github_parameters(values):
    if values.get("repo_owner") or values.get("repo_name"):
        logger.warning(
            "The repo_name and repo_owner keys are deprecated. Please use the github key."
        )

    assert (
        values.get("url")
        or values.get("github")
        or (values.get("repo_owner") and values.get("repo_name"))
    ), "Must specify `github` or `repo_owner` and `repo_name`"

    # Populate the `github` property if not already populated.
    if not values.get("github") and values.get("repo_name"):
        values["github"] = values[
            "url"
        ] = f"https://github.com/{values['repo_owner']}/{values['repo_name']}"
        values.pop("repo_owner")
        values.pop("repo_name")

    return values


def _sync_github_and_url(values):
    # If only github is provided, set url to github
    if values.get("github") and not values.get("url"):
        values["url"] = values["github"]
    # If only url is provided, set github to url
    elif values.get("url") and not values.get("github"):
        values["github"] = values["url"]
    return values


class GitHubDependencyPin(base_dependency.VcsDependencyPin):
    """Model representing a request to pin a GitHub dependency to a specific tag"""

    github: str

    @property
    def vcsTagResolver(self):  # -> Type["AbstractTagResolver"]:
        from cumulusci.core.dependencies.github_resolvers import (  # Circular imports
            GitHubTagResolver,
        )

        return GitHubTagResolver

    @root_validator(pre=True)
    def sync_vcs_and_url(cls, values):
        """Defined vcs should be assigned to url"""
        return _sync_github_and_url(values)


GitHubDependencyPin.update_forward_refs()


class BaseGitHubDependency(base_dependency.BaseVcsDynamicDependency, ABC):
    """Base class for dynamic dependencies that reference a GitHub repo."""

    github: Optional[AnyUrl] = None
    vcs: str = VCS_GITHUB
    pin_class = GitHubDependencyPin

    repo_owner: Optional[str] = None  # Deprecated - use full URL
    repo_name: Optional[str] = None  # Deprecated - use full URL

    @root_validator
    def check_deprecated_fields(cls, values):
        if values.get("repo_owner") or values.get("repo_name"):
            logger.warning(
                "The dependency keys `repo_owner` and `repo_name` are deprecated. Use the full repo URL with the `github` key instead."
            )
        return values

    @root_validator
    def validate_github_parameters(cls, values):
        return _validate_github_parameters(values)

    @root_validator(pre=True)
    def sync_vcs_and_url(cls, values):
        """Defined vcs should be assigned to url"""
        return _sync_github_and_url(values)


class GitHubDynamicSubfolderDependency(
    BaseGitHubDependency, base_dependency.VcsDynamicSubfolderDependency
):
    """A dependency expressed by a reference to a subfolder of a GitHub repo, which needs
    to be resolved to a specific ref. This is always an unmanaged dependency."""

    @property
    def unmanagedVcsDependency(self) -> Type["UnmanagedGitHubRefDependency"]:
        """A human-readable description of the dependency."""
        return UnmanagedGitHubRefDependency


class GitHubDynamicDependency(
    BaseGitHubDependency, base_dependency.VcsDynamicDependency
):
    """A dependency expressed by a reference to a GitHub repo, which needs
    to be resolved to a specific ref and/or package version."""

    @property
    def unmanagedVcsDependency(self) -> Type["UnmanagedGitHubRefDependency"]:
        """A human-readable description of the dependency."""
        return UnmanagedGitHubRefDependency

    def get_repo(self, context, url) -> "GitHubRepository":
        return get_github_repo(context, url)


class UnmanagedGitHubRefDependency(base_dependency.UnmanagedVcsDependency):
    """Static dependency on unmanaged metadata in a specific GitHub ref and subfolder."""

    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None

    # or
    github: Optional[AnyUrl] = None

    def get_repo(self, context, url) -> "GitHubRepository":
        return get_github_repo(context, url)

    @property
    def package_name(self) -> str:
        repo_owner, repo_name = split_repo_url((str(self.github)))
        package_name = f"{repo_owner}/{repo_name} {self.subfolder}"
        return package_name

    @root_validator
    def validate(cls, values):
        return _validate_github_parameters(values)

    @root_validator(pre=True)
    def sync_vcs_and_url(cls, values):
        """Defined vcs should be assigned to url"""

        return _sync_github_and_url(values)
