import functools
import logging
import re
from typing import Optional, Tuple

from cumulusci.core.config import BaseProjectConfig, UniversalConfig
from cumulusci.core.exceptions import VcsException, VcsNotFoundError
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.models import (
    AbstractBranch,
    AbstractGitTag,
    AbstractPullRequest,
    AbstractRef,
    AbstractRelease,
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
    vcs_service: VCSService = get_service_for_repo_url(config, config.repo_url)
    vcs_service.logger = logger or logging.getLogger(__name__)

    config.repo_service = vcs_service

    return vcs_service


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


@functools.lru_cache(50)
def get_repo_from_url(
    config: BaseProjectConfig, url: str, service_alias: Optional[str] = None
) -> AbstractRepo:
    vcs_service: VCSService = get_service_for_repo_url(
        config, url, service_alias=service_alias
    )

    repo = vcs_service.get_repository(options={"repository_url": url})

    if repo is None:
        raise VcsNotFoundError(f"Could not find a repository at {url}.")

    return repo


@functools.lru_cache(50)
def get_service_for_repo_url(
    config: BaseProjectConfig, url: str, service_alias: Optional[str] = None
) -> VCSService:
    """Determines the VCS service type for the repository."""

    for service in VCSService.registered_services():
        try:
            vcs_service: Optional[VCSService] = service.get_service_for_url(
                config, url, service_alias=service_alias
            )

            if vcs_service is None:
                continue

            return vcs_service
        except NotImplementedError:
            # If the service does not implement get_service_for_url, skip it
            continue

    raise VcsException(
        f"Could not find a VCS service for URL: {url}. "
        "Please ensure the URL is correct and the service is properly configured."
    )


@functools.lru_cache(50)
def get_remote_project_config(repo: AbstractRepo, ref: str) -> BaseProjectConfig:
    contents_io = repo.file_contents("cumulusci.yml", ref=ref)
    return BaseProjectConfig(UniversalConfig(), cci_safe_load(contents_io))


def find_repo_feature_prefix(repo: AbstractRepo) -> str:
    ref = repo.branch(repo.default_branch).commit.sha
    head_cumulusci_project_config = get_remote_project_config(repo, ref)
    return head_cumulusci_project_config.project__git__prefix_feature or "feature/"


def get_remote_context(
    repo: AbstractRepo, commit_status_context: str, default_context: str
) -> str:
    config = get_remote_project_config(repo, repo.default_branch)
    return config.lookup(f"project__git__{commit_status_context}") or default_context


def find_latest_release(
    repo: AbstractRepo, include_beta=None
) -> Optional[AbstractRelease]:
    try:
        if include_beta:
            return get_latest_prerelease(repo)
        else:
            return repo.latest_release()
    except (VcsNotFoundError, StopIteration):
        pass


def get_latest_prerelease(repo: AbstractRepo) -> Optional[AbstractRelease]:
    """Calls GraphQL to retrieve the latest release, ordered chronologically."""
    return repo.get_latest_prerelease()


def find_previous_release(repo: AbstractRepo, prefix=None):
    most_recent = None
    for release in repo.releases():
        if prefix and not release.tag_name.startswith(prefix):
            continue
        if not prefix and release.prerelease:
            continue
        # Return the second release
        if most_recent is None:
            most_recent = release
        else:
            return release


def locate_commit_status_package_id(
    remote_repo: AbstractRepo, release_branch: AbstractBranch, context_2gp: str
) -> Tuple[Optional[str], Optional[AbstractRepoCommit]]:
    """Given a branch on a remote repo, walk the first 5 commits looking
    for a commit status equal to context_2gp and attempt to parse a
    package version id from the commit status detail."""
    version_id = None
    count = 0
    commit: Optional[AbstractRepoCommit] = release_branch.commit
    while version_id is None and count < 5:
        version_id = get_version_id_from_commit(remote_repo, commit.sha, context_2gp)
        if version_id:
            break
        count += 1
        if commit.parents:
            commit = remote_repo.get_commit(commit.parents[0].sha)
        else:
            commit = None
            break

    return version_id, commit


def get_repo_from_config(config: BaseProjectConfig, options: dict = {}) -> AbstractRepo:
    """Get a repository from the project config."""
    vcs_service: VCSService = get_service(config, logger=config.logger)

    return vcs_service.get_repository(options=options)


def get_latest_tag(repo: AbstractRepo, beta: bool = False) -> str:
    """Query Github Releases to find the latest production or beta tag"""
    prefix = repo.project_config.project__git__prefix_release

    try:
        if not beta:
            release: Optional[AbstractRelease] = repo.latest_release()

            if not release.tag_name.startswith(prefix):
                return _get_latest_tag_for_prefix(repo, prefix)

            return release.tag_name
        else:
            return _get_latest_tag_for_prefix(
                repo, repo.project_config.project__git__prefix_beta
            )
    except Exception:
        raise VcsException(
            f"No release found for {repo.repo_url} with tag prefix {prefix}"
        )


def _get_latest_tag_for_prefix(repo: AbstractRepo, prefix: str) -> str:
    for release in repo.releases():
        if not release.tag_name.startswith(prefix):
            continue
        return release.tag_name
    raise VcsException(f"No release found for {repo.repo_url} with tag prefix {prefix}")


def get_version_id_from_tag(repo: AbstractRepo, tag_name: str) -> str:
    """Given the name of a tag, return the version_id in the tag's message.

    @param tag_name: the name of the tag
    @param repo: the repository of the package to look for a release in
    @returns: the 04t id in the tag's messages
    """
    tag = get_tag_by_name(repo, tag_name)
    for line in tag.message.split("\n"):
        if line.startswith("version_id:"):
            version_id = line.split("version_id: ")[1]
            if not version_id.startswith("04t"):
                continue
            return version_id

    raise VcsException(f"Could not find version_id for tag {tag_name}")
