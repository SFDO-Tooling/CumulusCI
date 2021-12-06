import abc
import itertools
from enum import Enum
from typing import Callable, Iterable, List, Optional, Tuple

from github3.exceptions import NotFoundError

from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.dependencies import (
    BaseGitHubDependency,
    Dependency,
    DynamicDependency,
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
    StaticDependency,
    parse_dependencies,
)
from cumulusci.core.dependencies.github import (
    get_package_data,
    get_package_details_from_tag,
    get_remote_project_config,
    get_repo,
)
from cumulusci.core.exceptions import CumulusCIException, DependencyResolutionError
from cumulusci.core.github import (
    find_latest_release,
    find_repo_2gp_context,
    find_repo_feature_prefix,
    get_version_id_from_commit,
)
from cumulusci.core.versions import PackageType
from cumulusci.utils.git import (
    construct_release_branch_name,
    get_feature_branch_name,
    get_release_identifier,
    is_release_branch_or_child,
)


class DependencyResolutionStrategy(str, Enum):
    """Enum that defines a strategy for resolving a dynamic dependency into a static dependency."""

    STATIC_TAG_REFERENCE = "tag"
    COMMIT_STATUS_EXACT_BRANCH = "commit_status_exact_branch"
    COMMIT_STATUS_RELEASE_BRANCH = "commit_status_release_branch"
    COMMIT_STATUS_PREVIOUS_RELEASE_BRANCH = "commit_status_previous_release_branch"
    BETA_RELEASE_TAG = "latest_beta"
    RELEASE_TAG = "latest_release"
    UNMANAGED_HEAD = "unmanaged"


class Resolver(abc.ABC):
    """Abstract base class for dependency resolution strategies."""

    name = "Resolver"

    @abc.abstractmethod
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        pass

    @abc.abstractmethod
    def resolve(
        self, dep: DynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        pass

    def __str__(self):
        return self.name


class GitHubTagResolver(Resolver):
    """Resolver that identifies a ref by a specific GitHub tag."""

    name = "GitHub Tag Resolver"

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, BaseGitHubDependency) and dep.tag is not None

    def resolve(
        self, dep: BaseGitHubDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        try:
            # Find the github release corresponding to this tag.
            repo = get_repo(dep.github, context)
            release = repo.release_from_tag(dep.tag)
            tag = repo.tag(repo.ref(f"tags/{release.tag_name}").object.sha)
            ref = tag.object.sha
            package_config = get_remote_project_config(repo, ref)
            package_name, namespace = get_package_data(package_config)
            version_id, package_type = get_package_details_from_tag(tag)

            install_unmanaged = (
                dep.is_unmanaged  # We've been told to use this dependency unmanaged
                or not (
                    # We will install managed if:
                    namespace  # the package has a namespace
                    or version_id  # or is a non-namespaced Unlocked Package
                )
            )

            if install_unmanaged:
                return ref, None
            else:
                if package_type is PackageType.SECOND_GEN:
                    package_dep = PackageVersionIdDependency(
                        version_id=version_id,
                        version_number=release.name,
                        package_name=package_name,
                    )
                else:
                    package_dep = PackageNamespaceVersionDependency(
                        namespace=namespace,
                        version=release.name,
                        package_name=package_name,
                        version_id=version_id,
                    )

                return (ref, package_dep)
        except NotFoundError:
            raise DependencyResolutionError(f"No release found for tag {dep.tag}")


class GitHubReleaseTagResolver(Resolver):
    """Resolver that identifies a ref by finding the latest GitHub release."""

    name = "GitHub Release Resolver"
    include_beta = False

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, BaseGitHubDependency)

    def resolve(
        self, dep: BaseGitHubDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        repo = get_repo(dep.github, context)
        release = find_latest_release(repo, include_beta=self.include_beta)
        if release:
            tag = repo.tag(repo.ref(f"tags/{release.tag_name}").object.sha)
            version_id, package_type = get_package_details_from_tag(tag)

            ref = tag.object.sha
            package_config = get_remote_project_config(repo, ref)
            package_name, namespace = get_package_data(package_config)

            install_unmanaged = (
                dep.is_unmanaged  # We've been told to use this dependency unmanaged
                or not (
                    # We will install managed if:
                    namespace  # the package has a namespace
                    or version_id  # or is a non-namespaced Unlocked Package
                )
            )

            if install_unmanaged:
                return ref, None
            else:
                if package_type is PackageType.SECOND_GEN:
                    package_dep = PackageVersionIdDependency(
                        version_id=version_id,
                        version_number=release.name,
                        package_name=package_name,
                    )
                else:
                    package_dep = PackageNamespaceVersionDependency(
                        namespace=namespace,
                        version=release.name,
                        package_name=package_name,
                        version_id=version_id,
                    )
                return (ref, package_dep)

        return (None, None)


class GitHubBetaReleaseTagResolver(GitHubReleaseTagResolver):
    """Resolver that identifies a ref by finding the latest GitHub release, including betas."""

    name = "GitHub Release Resolver (Betas)"
    include_beta = True


class GitHubUnmanagedHeadResolver(Resolver):
    """Resolver that identifies a ref by finding the latest commit on the main branch."""

    name = "GitHub Unmanaged Resolver"

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, BaseGitHubDependency)

    def resolve(
        self, dep: BaseGitHubDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        repo = get_repo(dep.github, context)
        return (repo.branch(repo.default_branch).commit.sha, None)


class GitHubReleaseBranchResolver(Resolver, abc.ABC):
    """Abstract base class for resolvers that use commit statuses on release branches to find refs."""

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return self.is_valid_repo_context(context) and isinstance(
            dep, BaseGitHubDependency
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

    def locate_commit_status_package_id(self, remote_repo, release_branch, context_2gp):
        version_id = None
        count = 0
        commit = release_branch.commit
        while version_id is None and count < 5:
            version_id = get_version_id_from_commit(
                remote_repo, commit.sha, context_2gp
            )
            if version_id:
                break
            count += 1
            if commit.parents:
                commit = remote_repo.commit(commit.parents[0]["sha"])
            else:
                commit = None
                break

        return version_id, commit


class GitHubReleaseBranchCommitStatusResolver(GitHubReleaseBranchResolver):
    """Resolver that identifies a ref by finding a beta package version
    in a commit status on a `feature/NNN` release branch."""

    name = "GitHub Release Branch Commit Status Resolver"
    branch_depth = 1

    def resolve(
        self, dep: BaseGitHubDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:

        release_id = self.get_release_id(context)
        repo = context.get_repo_from_url(dep.github)
        if not repo:
            raise DependencyResolutionError(
                f"Unable to access GitHub repository for {dep.github}"
            )

        try:
            remote_branch_prefix = find_repo_feature_prefix(repo)
            remote_2gp_context = find_repo_2gp_context(repo)
        except Exception:
            context.logger.info(
                f"Could not find feature branch prefix or commit-status context for {repo.clone_url}. Unable to resolve packages."
            )
            return (None, None)

        # We will check at least the release branch corresponding to our release id.
        # We may be configured to check backwards on release branches.
        release_branch = None
        for i in range(0, self.branch_depth):
            try:
                remote_matching_branch = construct_release_branch_name(
                    remote_branch_prefix, str(release_id - i)
                )

                release_branch = repo.branch(remote_matching_branch)
            except NotFoundError:
                pass

        if release_branch:
            version_id, commit = self.locate_commit_status_package_id(
                repo,
                release_branch,
                remote_2gp_context,
            )

            if version_id:
                context.logger.info(
                    f"Located package version {version_id} for release {release_id} on {repo.clone_url} at commit {release_branch.commit.sha}"
                )
                package_config = get_remote_project_config(repo, commit.sha)
                package_name, _ = get_package_data(package_config)

                return commit.sha, PackageVersionIdDependency(
                    version_id=version_id, package_name=package_name
                )

        context.logger.warn(
            f"No package version located for release {release_id} on {repo.clone_url}."
        )
        return (None, None)


class GitHubPreviousReleaseBranchCommitStatusResolver(
    GitHubReleaseBranchCommitStatusResolver
):
    """Resolver that identifies a ref by finding a beta package version
    in a commit status on a `feature/NNN` release branch that is earlier
    than the matching local release branch."""

    name = "GitHub Previous Release Branch Commit Status Resolver"
    branch_depth = 3


class GitHubReleaseBranchExactMatchCommitStatusResolver(GitHubReleaseBranchResolver):
    """Resolver that identifies a ref by finding a beta package version
    in a commit status on a branch whose name matches the local branch."""

    name = "GitHub Exact-Match Commit Status Resolver"

    def resolve(
        self, dep: BaseGitHubDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        release_id = self.get_release_id(context)

        repo = context.get_repo_from_url(dep.github)
        if not repo:
            raise DependencyResolutionError(
                f"Unable to access GitHub repository for {dep.github}"
            )

        try:
            remote_branch_prefix = find_repo_feature_prefix(repo)
            remote_2gp_context = find_repo_2gp_context(repo)
        except Exception:
            context.logger.info(
                f"Could not find feature branch prefix or commit-status context for {repo.clone_url}. Unable to resolve package."
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

        version_id, commit = self.locate_commit_status_package_id(
            repo,
            release_branch,
            remote_2gp_context,
        )

        if version_id:
            context.logger.info(
                f"Located package version {version_id} for release {release_id} on {repo.clone_url} at commit {release_branch.commit.sha}"
            )

            package_config = get_remote_project_config(repo, commit.sha)
            package_name, _ = get_package_data(package_config)

            return commit.sha, PackageVersionIdDependency(
                version_id=version_id, package_name=package_name
            )

        context.logger.warn(
            f"No package version located for release {release_id} on {repo.clone_url}."
        )
        return (None, None)


RESOLVER_CLASSES = {
    DependencyResolutionStrategy.STATIC_TAG_REFERENCE: GitHubTagResolver,
    DependencyResolutionStrategy.COMMIT_STATUS_EXACT_BRANCH: GitHubReleaseBranchExactMatchCommitStatusResolver,
    DependencyResolutionStrategy.COMMIT_STATUS_RELEASE_BRANCH: GitHubReleaseBranchCommitStatusResolver,
    DependencyResolutionStrategy.COMMIT_STATUS_PREVIOUS_RELEASE_BRANCH: GitHubPreviousReleaseBranchCommitStatusResolver,
    DependencyResolutionStrategy.BETA_RELEASE_TAG: GitHubBetaReleaseTagResolver,
    DependencyResolutionStrategy.RELEASE_TAG: GitHubReleaseTagResolver,
    DependencyResolutionStrategy.UNMANAGED_HEAD: GitHubUnmanagedHeadResolver,
}


## External API


def get_resolver(
    strategy: DependencyResolutionStrategy, dependency: DynamicDependency
) -> Optional[Resolver]:
    """Return an instance of a resolver class capable of applying the specified
    resolution strategy to the dependency."""
    # This will be fleshed out when further types of DynamicDependency are added.

    return RESOLVER_CLASSES[strategy]()


def get_resolver_stack(
    context: BaseProjectConfig, name: str
) -> List[DependencyResolutionStrategy]:
    """Return a sequence of resolution strategies identified by the given `name`,
    which can be either a named strategy from project__dependency_resolutions__resolution_strategies
    or an alias like `production`."""
    resolutions = context.project__dependency_resolutions
    stacks = context.project__dependency_resolutions__resolution_strategies

    if name in resolutions and name != "resolution_strategies":
        name = resolutions[name]

    if stacks and name in stacks:
        return [DependencyResolutionStrategy(n) for n in stacks[name]]

    raise CumulusCIException(f"Resolver stack {name} was not found.")


def dependency_filter_ignore_deps(ignore_deps: List[dict]) -> Callable:
    ignore_github = [d["github"] for d in ignore_deps if "github" in d]
    ignore_namespace = [d["namespace"] for d in ignore_deps if "namespace" in d]

    def should_include(some_dep: Dependency) -> bool:

        if isinstance(some_dep, PackageNamespaceVersionDependency):
            return some_dep.namespace not in ignore_namespace
        if isinstance(some_dep, BaseGitHubDependency):
            return some_dep.github not in ignore_github

        return True

    return should_include


def get_static_dependencies(
    context: BaseProjectConfig,
    dependencies: List[Dependency] = None,
    resolution_strategy: str = None,
    strategies: List[DependencyResolutionStrategy] = None,
    filter_function: Callable = None,
) -> List[StaticDependency]:
    """Resolves the dependencies of a CumulusCI project
    to convert dynamic GitHub dependencies into static dependencies
    by inspecting the referenced repositories.

    Keyword arguments:
    :param context: a project config
    :param dependencies: an optional list of dependencies to resolve
                         (defaults to project__dependencies from the project_config)
    :param resolution_strategy: name of a resolution strategy or stack
    :param strategies: list of resolution strategies to use
                       (specify this or resolution_strategy but not both)
    :param filter_function: if provided, call the function with each dependency
                            (including transitive ones) encountered, and include
                            those for which True is returned.
    """
    if dependencies is None:
        dependencies = parse_dependencies(context.project__dependencies)
    assert (resolution_strategy is None and strategies is not None) or (
        strategies is None and resolution_strategy is not None
    ), "Expected resolution_strategy or strategies but not both"
    if resolution_strategy:
        strategies = get_resolver_stack(context, resolution_strategy)
    if filter_function is None:
        filter_function = lambda x: True  # noqa: E731

    while any(not d.is_flattened or not d.is_resolved for d in dependencies):
        for d in dependencies:
            if isinstance(d, DynamicDependency) and not d.is_resolved:
                d.resolve(context, strategies)

        def unique(it: Iterable):
            seen = set()

            for each in it:
                if each not in seen:
                    seen.add(each)
                    yield each

        dependencies = list(
            unique(
                itertools.chain(
                    *list(
                        d.flatten(context) for d in dependencies if filter_function(d)
                    )
                ),
            )
        )

    # Make sure, if we had no flattening or resolving to do, that we apply the ignore list.
    return [d for d in dependencies if filter_function(d)]


def resolve_dependency(
    dependency: DynamicDependency,
    context: BaseProjectConfig,
    strategies: List[DependencyResolutionStrategy],
):
    """Resolve a DynamicDependency that is not pinned to a specific version into one that is.

    If successful, sets `dependency.ref` and optionally `dependency.package_dependency`
    (if a package release is found).

    Otherwise raises DependencyResolutionError.
    """

    if dependency.is_resolved:
        return

    for s in strategies:
        resolver = get_resolver(s, dependency)

        if resolver and resolver.can_resolve(dependency, context):
            try:
                dependency.ref, dependency.package_dependency = resolver.resolve(
                    dependency, context
                )
                if dependency.package_dependency:
                    try:
                        dependency.package_dependency.password_env_name = (
                            dependency.password_env_name
                        )
                    except AttributeError:  # pragma: no cover
                        pass
                if dependency.ref:
                    break
            except DependencyResolutionError:
                context.logger.info(
                    f"Resolution strategy {s} failed for dependency {dependency}."
                )

    if not dependency.ref:
        raise DependencyResolutionError(f"Unable to resolve dependency {dependency}")
