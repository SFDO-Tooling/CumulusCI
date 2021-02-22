import abc
from cumulusci.core.dependencies.dependencies import (
    DynamicDependency,
    GitHubDynamicDependency,
    ManagedPackageDependency,
)
import io
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load
from github3.exceptions import NotFoundError
from cumulusci.core.exceptions import DependencyResolutionError
from enum import Enum, auto
from typing import Optional, Tuple
from cumulusci.core.config.project_config import BaseProjectConfig

from cumulusci.core.github import (
    find_latest_release,
    find_repo_feature_prefix,
    get_version_id_from_commit,
)
from cumulusci.utils.git import (
    get_feature_branch_name,
    is_release_branch_or_child,
    construct_release_branch_name,
    get_release_identifier,
)


class DependencyResolutionStrategy(Enum):
    STRATEGY_STATIC_TAG_REFERENCE = auto()
    STRATEGY_2GP_EXACT_BRANCH = auto()
    STRATEGY_2GP_RELEASE_BRANCH = auto()
    STRATEGY_2GP_PREVIOUS_RELEASE_BRANCH = auto()
    STRATEGY_BETA_RELEASE_TAG = auto()
    STRATEGY_RELEASE_TAG = auto()
    STRATEGY_UNMANAGED_HEAD = auto()


class Resolver(abc.ABC):
    @abc.abstractmethod
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        pass

    @abc.abstractmethod
    def resolve(
        self, dep: DynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[ManagedPackageDependency]]:
        pass


class GitHubTagResolver(Resolver):
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, GitHubDynamicDependency) and dep.tag is not None

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[ManagedPackageDependency]]:
        try:
            # Find the github release corresponding to this tag.
            repo = dep.get_repo(context)
            release = repo.release_from_tag(dep.tag)

            return (
                repo.tag(repo.ref(f"tags/{release.tag_name}").object.sha).object.sha,
                ManagedPackageDependency(
                    namespace=context.project__package__namespace, version=release.name
                ),
            )
        except NotFoundError:
            raise DependencyResolutionError(f"No release found for tag {dep.tag}")


class GitHubReleaseTagResolver(Resolver):
    include_beta = False

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, GitHubDynamicDependency)

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[ManagedPackageDependency]]:
        repo = dep.get_repo(context)
        release = find_latest_release(repo, include_beta=self.include_beta)
        if release:
            ref = repo.tag(repo.ref(f"tags/{release.tag_name}").object.sha).object.sha

            contents = repo.file_contents("cumulusci.yml", ref=ref)
            cumulusci_yml = cci_safe_load(io.StringIO(contents.decoded.decode("utf-8")))

            # Get the namespace from the cumulusci.yml if set
            package_config = cumulusci_yml.get("project", {}).get("package", {})
            namespace = package_config.get("namespace")
            package_name = package_config.get("name_managed") or package_config.get(
                "name"
            )

            return (
                ref,
                ManagedPackageDependency(
                    namespace=namespace, version=release.name, package_name=package_name
                ),
            )

        return (None, None)


class GitHubBetaReleaseTagResolver(Resolver):
    include_beta = True


class GitHubUnmanagedHeadResolver(Resolver):
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, GitHubDynamicDependency) and dep.tag is not None

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[ManagedPackageDependency]]:
        repo = dep.get_repo(context)
        return (repo.branch(repo.default_branch).commit.sha, None)


def _locate_2gp_package_id(remote_repo, release_branch, context_2gp):
    version_id = None
    count = 0
    commit = release_branch.commit
    while version_id is None and count < 5:
        version_id = get_version_id_from_commit(remote_repo, commit.sha, context_2gp)
        if version_id:
            break
        count += 1
        if commit.parents:
            commit = remote_repo.commit(commit.parents[0]["sha"])
        else:
            break

    return version_id, commit


class GitHubReleaseBranchMixin:
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return self.is_valid_repo_context(context) and isinstance(
            dep, GitHubDynamicDependency
        )

    def get_release_id(self, context: BaseProjectConfig) -> int:
        if not context.repo_branch or not context.project__git__prefix_feature:
            raise DependencyResolutionError(
                "Cannot get current branch or feature branch prefix"
            )
        release_id = get_release_identifier(
            context.repo_branch, context.project__git__prefix_feature
        )
        if not release_id:
            raise DependencyResolutionError("Cannot get current release identifier")

        return int(release_id)

    def is_valid_repo_context(self, context) -> bool:
        return (
            context.repo_branch
            and context.project__git__prefix_feature
            and is_release_branch_or_child(
                context.repo_branch, context.project__git__prefix_feature
            )
        )


class GitHubReleaseBranch2GPResolver(Resolver, GitHubReleaseBranchMixin):
    branch_depth = 1

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[ManagedPackageDependency]]:

        release_id = self.get_release_id(context)
        if not release_id:
            raise DependencyResolutionError("Cannot get current release identifier")

        release_id = int(release_id)

        repo = context.get_github_repo(dep.github)
        if not repo:
            raise DependencyResolutionError(
                f"Unable to access GitHub repository for {dep.github}"
            )

        try:
            remote_branch_prefix = find_repo_feature_prefix(repo)
        except Exception:
            context.logger.info(
                f"Could not find feature branch prefix for {repo.clone_url}. Unable to resolve 2GP packages."
            )
            return (None, None)

        # We will check at least the release branch corresponding to our release id.
        # We may be configured to check backwards on release branches.
        release_branch = None
        for i in range(0, self.branch_depth + 1):
            try:
                remote_matching_branch = construct_release_branch_name(
                    remote_branch_prefix, str(release_id - i)
                )

                release_branch = repo.branch(remote_matching_branch)
            except NotFoundError:
                pass

        if release_branch:
            version_id, commit = _locate_2gp_package_id(
                repo, release_branch, context.project__git__2gp_context
            )

            if version_id:
                context.logger.info(
                    f"Located 2GP package version {version_id} for release {release_id} on {repo.clone_url} at commit {release_branch.commit.sha}"
                )

                return commit.sha, ManagedPackageDependency(version_id=version_id)

        context.logger.warn(
            f"No 2GP package version located for release {release_id} on {repo.clone_url}."
        )
        return (None, None)


class GitHubPreviousReleaseBranch2GPResolver(GitHubReleaseBranch2GPResolver):
    branch_depth = 3


class GitHubReleaseBranchExactMatch2GPResolver(Resolver, GitHubReleaseBranchMixin):
    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[ManagedPackageDependency]]:
        release_id = self.get_release_id(context)

        repo = context.get_github_repo(dep.github)
        if not repo:
            raise DependencyResolutionError(f"Unable to access repository {dep.github}")

        try:
            remote_branch_prefix = find_repo_feature_prefix(repo)
        except Exception:
            context.logger.info(
                f"Could not find feature branch prefix for {repo.clone_url}. Unable to resolve 2GP packages."
            )
            return (None, None)

        # Attempt exact match
        try:
            branch = get_feature_branch_name(
                context.repo_branch, context.project__git__prefix_feature
            )
            release_branch = repo.branch(f"{remote_branch_prefix}{branch}")
        except Exception:
            context.logger.info(f"Exact-match branch not found for {repo.clone_url}.")
            return (None, None)

        version_id, commit = _locate_2gp_package_id(
            repo,
            release_branch,
            context.project__git__prefix_feature,  # FIXME: This is supposed to be context_2gp
        )

        if version_id:
            context.logger.info(
                f"Located 2GP package version {version_id} for release {release_id} on {repo.clone_url} at commit {release_branch.commit.sha}"
            )

            return commit.sha, ManagedPackageDependency(version_id=version_id)

        context.logger.warn(
            f"No 2GP package version located for release {release_id} on {repo.clone_url}."
        )
        return (None, None)


RESOLVER_CLASSES = {
    DependencyResolutionStrategy.STRATEGY_STATIC_TAG_REFERENCE: GitHubTagResolver,
    DependencyResolutionStrategy.STRATEGY_2GP_EXACT_BRANCH: GitHubReleaseBranchExactMatch2GPResolver,
    DependencyResolutionStrategy.STRATEGY_2GP_RELEASE_BRANCH: GitHubReleaseBranch2GPResolver,
    DependencyResolutionStrategy.STRATEGY_2GP_PREVIOUS_RELEASE_BRANCH: GitHubPreviousReleaseBranch2GPResolver,
    DependencyResolutionStrategy.STRATEGY_BETA_RELEASE_TAG: GitHubBetaReleaseTagResolver,
    DependencyResolutionStrategy.STRATEGY_RELEASE_TAG: GitHubReleaseTagResolver,
    DependencyResolutionStrategy.STRATEGY_UNMANAGED_HEAD: GitHubUnmanagedHeadResolver,
}


def get_resolver(
    strategy: DependencyResolutionStrategy, dependency: DynamicDependency
) -> Optional[Resolver]:
    # This will be fleshed out when further types of DynamicDependency are added.
    return RESOLVER_CLASSES[strategy]()
