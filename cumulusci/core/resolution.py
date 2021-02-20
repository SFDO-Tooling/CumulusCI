import abc
import io
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load
from github3.exceptions import NotFoundError
import pydantic
from cumulusci.core.exceptions import DependencyResolutionError
from enum import Enum, auto
from typing import Optional, List, Union, Tuple
from pydantic import BaseModel
from cumulusci.core.config import OrgConfig
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

# We have three total jobs to do:
# - Resolve dynamic dependencies to a ref, and optionally a managed package version
# - Flatten dependencies into fully-specified steps
# - Install flattened dependencies

# This module takes over jobs 1 and 2 from ProjectConfig
# Dependency objects will have an `install()` method that calls to services elsewhere.


class DependencyResolutionStrategy(Enum):
    STRATEGY_STATIC_TAG_REFERENCE = auto()
    STRATEGY_2GP_EXACT_BRANCH = auto()
    STRATEGY_2GP_RELEASE_BRANCH = auto()
    STRATEGY_2GP_PREVIOUS_RELEASE_BRANCH = auto()
    STRATEGY_BETA_RELEASE_TAG = auto()
    STRATEGY_RELEASE_TAG = auto()
    STRATEGY_UNMANAGED_HEAD = auto()


class Dependency(BaseModel, abc.ABC):
    @property
    @abc.abstractmethod
    def is_resolved(self):
        return False

    @property
    @abc.abstractmethod
    def is_flattened(self):
        return False


class DynamicDependency(Dependency, abc.ABC):
    @property
    def is_flattened(self):
        return False

    def resolve(
        self, context: BaseProjectConfig, strategies: List[DependencyResolutionStrategy]
    ):
        if self.is_resolved:
            return

        for s in strategies:
            resolver = get_resolver(s, self)

            if resolver.can_resolve(self, context):
                try:
                    self.ref, self.managed_dependency = resolver.resolve(self, context)
                    if self.ref:
                        break
                except DependencyResolutionError:
                    context.logger.info(
                        f"Resolution strategy {s} failed for dependency {self}."
                    )


class StaticDependency(Dependency, abc.ABC):
    @abc.abstractmethod
    def install(self, org_config: OrgConfig):
        pass

    @property
    def is_resolved(self):
        return True

    @property
    def is_flattened(self):
        return True


class GitHubDynamicDependency(DynamicDependency):
    github: Optional[str]
    release: Optional[str]  # latest_beta, previous (?)

    unmanaged: bool = False
    subfolder: Optional[str]
    # Do we need the namespace injection ones here too?

    tag: Optional[
        str
    ]  # QUESTION: can a `tag` specifier identify a managed release or just a ref for unmanaged?
    ref: Optional[str]

    repo_owner: Optional[str]  # This should be deprecated as it's GitHub-specific
    repo_name: Optional[str]  # This should be deprecated as it's GitHub-specific

    dependencies: Optional[List[dict]]  # How do we handle this?
    skip: Optional[List[str]]

    # UI options
    name: Optional[str]  # Can this be inferred? Is it ever specified in markup?

    @property
    def is_resolved(self):
        return self.ref is not None

    @pydantic.root_validator
    def check_complete(cls, values):
        assert "github" in values or (
            "repo_owner" in values and "repo_name" in values
        ), "Must specify `github` or `repo_owner` and `repo_name`"
        assert None in [
            values.get("tag"),
            values.get("ref"),
        ], "Must not specify both `tag` and `ref`"
        assert None in [
            values.get("tag"),
            values.get("release"),
        ], "Must not specify both `tag` and `release`"
        assert None in [
            values.get("release"),
            values.get("ref"),
        ], "Must not specify both `release` and `ref`"

    def flatten(self):
        pass


class ManagedPackageDependency(StaticDependency):
    namespace: Optional[str]
    version: Optional[str]
    package_version_id: Optional[str] = pydantic.Field(alias="version_id")
    package_name: Optional[str]

    @property
    def is_resolved(self):
        return True

    @property
    def is_flattened(self):
        return True

    @property
    def package(self):
        return self.package_name or self.namespace

    @property
    def step_name(self):
        return (
            f"Install {self.package} version {self.package_version_id or self.version}"
        )

    def install(self):
        pass  # TODO

    @pydantic.root_validator
    def validate(cls, values):
        assert (
            "namespace" in values and "version" in values
        ) or "package_version_id" in values, (
            "Must specify `namespace` and `version`, or `package_version_id`"
        )


class UnmanagedDependency(StaticDependency):
    zip_url: Optional[str]

    # or
    repo_owner: Optional[str]  # This should be deprecated as it's GitHub-specific
    repo_name: Optional[str]  # This should be deprecated as it's GitHub-specific

    # or
    repo_url: Optional[str]

    # and
    ref: Optional[str]

    subfolder: Optional[str]
    namespace_inject: Optional[str]
    namespace_strip: Optional[str]

    @pydantic.root_validator
    def validate(cls, values):
        if "repo_name" in values or "repo_owner" in values:
            logger.warn(
                "The repo_name and repo_owner keys are deprecated. Pleas use repo_url."
            )

        assert (
            "zip_url" in values
            or ("repo_url" in values and "ref" in values)
            or ("repo_name" in values and "repo_owner" in values and "ref" in values)
        ), "Must specify `zip_url`, or `repo_url` and `ref`"


def parse_dependency(
    dep_dict: dict,
) -> Optional[Union[DynamicDependency, StaticDependency]]:
    for dependency_class in [
        GitHubDynamicDependency,
        ManagedPackageDependency,
        UnmanagedDependency,
    ]:
        try:
            dep = dependency_class.parse_obj(dep_dict)
            if dep:
                return dep
        except pydantic.ValidationError:
            pass


## Resolvers


# project:
#    resolutions:
#        stacks:
#           allow_betas:
#            - 2gp_exact_match
#            - managed_beta
#            - managed_release
#           2gp_pref:
#            - 2gp_exact_match
#            - managed_release
#        default_stack: latest_prod


# How should per-dependency resolver specification interact with the project-level
# specification used by the lowest-level dependency?
#    dependencies:
#        - github: https://foo/
#          resolver_stack: latest_beta


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
            repo = context.get_github_repo(dep.github)
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
        repo = context.get_github_repo(dep.github)
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
        repo = context.get_github_repo(
            dep.github
        )  # TODO: all these calls miss the name/owner mechanic
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


class GitHubReleaseBranch2GPResolver(Resolver):
    branch_depth = 1

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, GitHubDynamicDependency) and is_release_branch_or_child(
            context.repo_branch, context.project__git__prefix_feature
        )

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[ManagedPackageDependency]]:
        release_id = int(
            get_release_identifier(
                context.repo_branch, context.project__git__prefix_feature
            )
            or 0
        )

        repo = context.get_github_repo(dep.github)

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


class GitHubReleaseBranchExactMatch2GPResolver(Resolver):
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, GitHubDynamicDependency) and is_release_branch_or_child(
            context.repo_branch, context.project__git__prefix_feature
        )

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[ManagedPackageDependency]]:
        release_id = int(
            get_release_identifier(
                context.repo_branch, context.project__git__prefix_feature
            )
            or 0
        )

        repo = context.get_github_repo(dep.github)

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
            repo, release_branch, context.project__git__prefix_feature
        )

        if version_id:
            context.logger.info(
                f"Located 2GP package version {version_id} for release {release_id} on {repo.clone_url} at commit {release_branch.commit.sha}"
            )

            return version_id, commit.sha

        context.logger.warn(
            f"No 2GP package version located for release {release_id} on {repo.clone_url}. Falling back to 1GP."
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
