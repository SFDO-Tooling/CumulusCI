from collections import namedtuple
from cumulusci.core.dependencies.github import (
    get_package_data,
    get_remote_project_config,
    get_repo,
)
from cumulusci.utils.yaml.model_parser import CCIModel
import logging
from typing import Iterable, List, Optional, Tuple

import pydantic
from github3.exceptions import NotFoundError
from github3.repos.repo import Repository
from pydantic.networks import AnyUrl

from cumulusci.core.config import OrgConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.exceptions import DependencyResolutionError, DependencyParseError
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    PackageInstallOptions,
    install_package_by_namespace_version,
    install_package_by_version_id,
)
from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder
from cumulusci.utils import download_extract_github_from_repo, download_extract_zip
from cumulusci.utils.git import split_repo_url
import abc

from cumulusci.core.github import (
    find_latest_release,
    find_repo_2gp_context,
    find_repo_feature_prefix,
    get_version_id_from_commit,
)
from cumulusci.utils.git import (
    get_feature_branch_name,
    is_release_branch_or_child,
    construct_release_branch_name,
    get_release_identifier,
)

from cumulusci.core.dependencies.utils import TaskContext

from enum import Enum

from cumulusci.core.exceptions import CumulusCIException
import itertools


logger = logging.getLogger(__name__)


class HashableBaseModel(CCIModel):
    """Base Pydantic model class that has a functional `hash()` method.
    Requires that model can be converted to JSON."""

    # See https://github.com/samuelcolvin/pydantic/issues/1303
    def __hash__(self):
        return hash((type(self),) + tuple(self.json()))


class DependencyResolutionStrategy(str, Enum):
    """Enum that defines a strategy for resolving a dynamic dependency into a static dependency."""

    STRATEGY_STATIC_TAG_REFERENCE = "tag"
    STRATEGY_2GP_EXACT_BRANCH = "exact_branch_2gp"
    STRATEGY_2GP_RELEASE_BRANCH = "release_branch_2gp"
    STRATEGY_2GP_PREVIOUS_RELEASE_BRANCH = "previous_release_branch_2gp"
    STRATEGY_BETA_RELEASE_TAG = "latest_beta"
    STRATEGY_RELEASE_TAG = "latest_release"
    STRATEGY_UNMANAGED_HEAD = "unmanaged"


class Dependency(HashableBaseModel, abc.ABC):
    """Abstract base class for models representing dependencies

    Dependencies can be _resolved_ to an immutable version, or not.
    They can also be _flattened_ (turned into a list including their own transitive dependencies) or not.
    """

    @property
    @abc.abstractmethod
    def name(self):
        pass

    @property
    @abc.abstractmethod
    def description(self):
        pass

    @property
    @abc.abstractmethod
    def is_resolved(self):
        return False  # pragma: no cover

    @property
    @abc.abstractmethod
    def is_flattened(self):
        return False  # pragma: no cover

    def flatten(self, context: BaseProjectConfig) -> List["Dependency"]:
        """Get a list including this dependency as well as its transitive dependencies."""
        return [self]

    def resolve(
        self, context: BaseProjectConfig, strategies: List[DependencyResolutionStrategy]
    ):
        """Resolve a dependency that is not pinned to a specific version into one that is."""
        pass  # pragma: no cover

    def __str__(self):
        return self.name


Dependency.update_forward_refs()


class StaticDependency(Dependency, abc.ABC):
    """Abstract base class for dependencies that we know how to install (i.e., they
    are already both resolved and flattened)."""

    @abc.abstractmethod
    def install(self, org_config: OrgConfig, retry_options: dict = None):
        pass  # pragma: no cover

    @property
    def is_resolved(self):
        return True

    @property
    def is_flattened(self):
        return True


class DynamicDependency(Dependency, abc.ABC):
    """Abstract base class for dependencies with dynamic references, like GitHub.
    These dependencies must be resolved and flattened before they can be installed."""

    managed_dependency: Optional[StaticDependency]

    @property
    def is_flattened(self):
        return False

    def resolve(
        self, context: BaseProjectConfig, strategies: List[DependencyResolutionStrategy]
    ):
        """Try to resolve this dependency using the specified strategies.

        If successful, sets `self.ref` and optionally `self.managed_dependency`
        (if a package release is found).

        Otherwise raises DependencyResolutionError.
        """

        if self.is_resolved:
            return

        for s in strategies:
            resolver = get_resolver(s, self)

            if resolver and resolver.can_resolve(self, context):
                try:
                    context.logger.debug(f"Attempting to resolve {self} via {resolver}")
                    self.ref, self.managed_dependency = resolver.resolve(self, context)
                    if self.ref:
                        context.logger.debug(
                            f"Resolved {self} to {self.ref} (package {self.managed_dependency})"
                        )
                        break
                except DependencyResolutionError:
                    context.logger.info(
                        f"Resolution strategy {s} failed for dependency {self}."
                    )

        if not self.ref:
            raise DependencyResolutionError(f"Unable to resolve dependency {self}")


class Resolver(abc.ABC):
    """Abstract base class for dependency resolution strategies."""

    name = "Resolver"

    @abc.abstractmethod
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        pass  # pragma: no cover

    @abc.abstractmethod
    def resolve(
        self, dep: DynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        pass  # pragma: no cover

    def __str__(self):
        return self.name


class GitHubDynamicDependency(DynamicDependency):
    """A dependency expressed by a reference to a GitHub repo, which needs
    to be resolved to a specific ref and/or package version."""

    github: Optional[AnyUrl]

    repo_owner: Optional[str]  # Deprecated - use full URL
    repo_name: Optional[str]  # Deprecated - use full URL

    unmanaged: bool = False
    subfolder: Optional[str]
    namespace_inject: Optional[str]
    namespace_strip: Optional[str]

    tag: Optional[str]
    ref: Optional[str]

    skip: List[str] = []

    @property
    def is_resolved(self):
        return self.ref is not None

    @pydantic.root_validator
    def check_deprecated_fields(cls, values):
        if values.get("repo_owner") or values.get("repo_name"):
            logger.warning(
                "The dependency keys `repo_owner` and `repo_name` are deprecated. Use the full repo URL with the `github` key instead."
            )
        return values

    @pydantic.root_validator
    def check_complete(cls, values):
        assert values.get("github") or (
            values.get("repo_owner") and values.get("repo_name")
        ), "Must specify `github` or `repo_owner` and `repo_name`"
        assert values["ref"] is None, "Must not specify `ref` at creation."

        # Populate the `github` and `repo_name`, `repo_owner` properties if not already populated.
        if not values.get("repo_name"):
            values["repo_owner"], values["repo_name"] = split_repo_url(values["github"])

        if not values.get("github"):
            values[
                "github"
            ] = f"https://github.com/{values['repo_owner']}/{values['repo_name']}"

        return values

    def _flatten_unpackaged(
        self,
        repo: Repository,
        subfolder: str,
        skip: List[str],
        managed: bool,
        namespace: Optional[str],
    ) -> List[StaticDependency]:
        """Locate unmanaged dependencies from a repository subfolder (such as unpackaged/pre or unpackaged/post)"""
        unpackaged = []
        try:
            contents = repo.directory_contents(subfolder, return_as=dict, ref=self.ref)
        except NotFoundError:
            contents = None

        if contents:
            for dirname in list(contents.keys()):
                this_subfolder = f"{subfolder}/{dirname}"
                if this_subfolder in skip:
                    continue

                unpackaged.append(
                    UnmanagedGitHubRefDependency(
                        github=self.github,
                        ref=self.ref,
                        subfolder=this_subfolder,
                        unmanaged=not managed,
                        namespace_inject=namespace if namespace and managed else None,
                        namespace_strip=namespace
                        if namespace and not managed
                        else None,
                    )
                )

        return unpackaged

    def flatten(self, context: BaseProjectConfig) -> List[Dependency]:
        """Find more dependencies based on repository contents.

        Includes:
        - dependencies from cumulusci.yml
        - subfolders of unpackaged/pre
        - the contents of src, if this is not a managed package
        - subfolders of unpackaged/post
        """
        if not self.is_resolved or not self.ref:
            raise DependencyResolutionError(
                f"Dependency {self.github} is not resolved and cannot be flattened."
            )

        deps = []

        context.logger.info(f"Collecting dependencies from Github repo {self.github}")
        repo = get_repo(self.github, context)

        package_config = get_remote_project_config(repo, self.ref)
        _, namespace = get_package_data(package_config)

        # Parse upstream dependencies from the repo's cumulusci.yml
        # These may be unresolved or unflattened; if so, `get_static_dependencies()`
        # will manage them.
        dependencies = package_config.project__dependencies
        if dependencies:
            deps.extend([parse_dependency(d) for d in dependencies])
            if None in deps:
                raise DependencyResolutionError(
                    "Unable to flatten dependency {self} because a transitive dependency could not be parsed."
                )

        # Check for unmanaged flag on a namespaced package
        managed = bool(namespace and not self.unmanaged)

        # Look for subfolders under unpackaged/pre
        # unpackaged/pre is always deployed unmanaged, no namespace manipulation.
        deps.extend(
            self._flatten_unpackaged(
                repo, "unpackaged/pre", self.skip, managed=False, namespace=None
            )
        )

        # Look for metadata under src (deployed if no namespace, or we're asked to do an unmanaged install)
        if not managed:
            contents = repo.directory_contents("src", ref=self.ref)
            if contents:
                deps.append(
                    UnmanagedGitHubRefDependency(
                        github=self.github,
                        ref=self.ref,
                        subfolder="src",
                        unmanaged=self.unmanaged,
                        namespace_inject=self.namespace_inject,
                        namespace_strip=self.namespace_strip,
                    )
                )
        else:
            if self.managed_dependency is None:
                raise DependencyResolutionError(
                    f"Could not find latest release for {self}"
                )

            deps.append(self.managed_dependency)

        # We always inject the project's namespace into unpackaged/post metadata if managed
        deps.extend(
            self._flatten_unpackaged(
                repo,
                "unpackaged/post",
                self.skip,
                managed=managed,
                namespace=namespace,
            )
        )

        return deps

    @property
    def name(self):
        return f"Dependency: {self.github}"

    @property
    def description(self):
        subfolder = f"/{self.subfolder}" if self.subfolder else ""
        unmanaged = " (unmanaged)" if self.unmanaged else ""
        loc = f" @{self.ref or self.tag}" if self.ref or self.tag else ""
        return f"{self.name}{subfolder}{unmanaged}{loc}"


class PackageNamespaceVersionDependency(StaticDependency):
    """Static dependency on a package identified by namespace and version number."""

    namespace: str
    version: str
    package_name: Optional[str]

    @property
    def package(self):
        return self.package_name or self.namespace or "Unknown Package"

    def install(
        self,
        context: BaseProjectConfig,
        org: OrgConfig,
        options: PackageInstallOptions = None,
    ):
        if not options:
            options = PackageInstallOptions()

        context.logger.info(f"Installing {self.package} version {self.version}")
        install_package_by_namespace_version(
            context,
            org,
            self.namespace,
            self.version,
            options,
            retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
        )

    @property
    def name(self):
        return f"Install {self.package} {self.version}"

    @property
    def description(self):
        return self.name


class PackageVersionIdDependency(StaticDependency):
    """Static dependency on a package identified by 04t version id."""

    version_id: str
    package_name: Optional[str]

    @property
    def package(self):
        return self.package_name or "Unknown Package"

    def install(
        self,
        context: BaseProjectConfig,
        org: OrgConfig,
        options: PackageInstallOptions = None,
    ):
        if not options:
            options = PackageInstallOptions()

        context.logger.info(f"Installing {self.package} {self.version_id}")
        install_package_by_version_id(
            context,
            org,
            self.version_id,
            options,
            retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
        )

    @property
    def name(self):
        return f"Install {self.package} {self.version_id}"

    @property
    def description(self):
        return self.name


class UnmanagedDependency(StaticDependency, abc.ABC):
    """Abstract base class for static, unmanaged dependencies."""

    unmanaged: Optional[bool]
    subfolder: Optional[str]
    namespace_inject: Optional[str]
    namespace_strip: Optional[str]

    def _get_unmanaged(self, org: OrgConfig):
        if self.unmanaged is None and self.namespace_inject:
            return self.namespace_inject not in org.installed_packages

        return self.unmanaged

    @abc.abstractmethod
    def _get_zip_src(self, context: BaseProjectConfig):
        pass

    def install(self, context: BaseProjectConfig, org: OrgConfig):
        zip_src = self._get_zip_src(context)

        context.logger.info(f"Deploying unmanaged metadata from {self.description}")

        # Determine whether to inject namespace prefixes or not
        # If and only if we have no explicit configuration.

        options = {
            "unmanaged": self._get_unmanaged(org),
            "namespace_inject": self.namespace_inject,
            "namespace_strip": self.namespace_strip,
        }

        package_zip = MetadataPackageZipBuilder.from_zipfile(
            zip_src, options=options, logger=logger
        ).as_base64()
        task = TaskContext(org_config=org, project_config=context, logger=logger)

        api = ApiDeploy(task, package_zip)
        return api()


class UnmanagedGitHubRefDependency(UnmanagedDependency):
    """Static dependency on unmanaged metadata in a specific GitHub ref and subfolder."""

    repo_owner: Optional[str]
    repo_name: Optional[str]

    # or
    github: Optional[AnyUrl]

    # and
    ref: str

    @pydantic.root_validator
    def validate(cls, values):
        if values.get("repo_owner") or values.get("repo_name"):
            logger.warning(
                "The repo_name and repo_owner keys are deprecated. Please use the github key."
            )
        assert None in [
            values.get("repo_owner"),
            values.get("github"),
        ], "Must specify `repo_owner` or `github`, but not both."

        # Populate the `github` and `repo_name, `repo_owner` properties if not already populated.
        if (not values.get("repo_name") or not values.get("repo_owner")) and values.get(
            "github"
        ):
            values["repo_owner"], values["repo_name"] = split_repo_url(values["github"])

        if not values.get("github") and values.get("repo_name"):
            values[
                "github"
            ] = f"https://github.com/{values['repo_owner']}/{values['repo_name']}"

        return values

    def _get_zip_src(self, context):
        return download_extract_github_from_repo(
            get_repo(self.github, context),
            self.subfolder,
            ref=self.ref,
        )

    @property
    def name(self):
        subfolder = (
            f"/{self.subfolder}" if self.subfolder and self.subfolder != "src" else ""
        )
        return f"Deploy {self.github}{subfolder}"

    @property
    def description(self):
        return f"{self.name} @{self.ref}"


class UnmanagedZipURLDependency(UnmanagedDependency):
    """Static dependency on unmanaged metadata downloaded as a zip file from a URL."""

    zip_url: AnyUrl

    def _get_zip_src(self, context: BaseProjectConfig):
        return download_extract_zip(self.zip_url, subfolder=self.subfolder)

    @property
    def name(self):
        subfolder = f"/{self.subfolder}" if self.subfolder else ""

        return f"Deploy {self.zip_url} {subfolder}"

    @property
    def description(self):
        return self.name


def parse_dependencies(deps: Optional[List[dict]]) -> List[Dependency]:
    """Convert a list of dependency specifications in the form of dicts
    (as defined in `cumulusci.yml`) and parse each into a concrete Dependency subclass.

    Throws DependencyParseError if a dict cannot be parsed."""
    parsed_deps = [parse_dependency(d) for d in deps or []]
    if None in parsed_deps:
        raise DependencyParseError("Unable to parse dependencies")

    return parsed_deps


def parse_dependency(dep_dict: dict) -> Optional[Dependency]:
    """Parse a single dependency specification in the form of a dict
    into a concrete Dependency subclass.

    Returns None if the given dict cannot be parsed."""

    for dependency_class in [
        PackageNamespaceVersionDependency,
        PackageVersionIdDependency,
        GitHubDynamicDependency,
        UnmanagedGitHubRefDependency,
        UnmanagedZipURLDependency,
    ]:
        try:
            dep = dependency_class.parse_obj(dep_dict)
            if dep:
                return dep
        except pydantic.ValidationError:
            pass


## Resolvers


class GitHubTagResolver(Resolver):
    """Resolver that identifies a ref by a specific GitHub tag."""

    name = "GitHub Tag Resolver"

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, GitHubDynamicDependency) and dep.tag is not None

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        try:
            # Find the github release corresponding to this tag.
            repo = get_repo(dep.github, context)
            release = repo.release_from_tag(dep.tag)
            ref = repo.tag(repo.ref(f"tags/{release.tag_name}").object.sha).object.sha
            package_config = get_remote_project_config(repo, ref)
            package_name, namespace = get_package_data(package_config)

            if not dep.unmanaged and not namespace:
                raise DependencyResolutionError(
                    f"The tag {dep.tag} in {dep.github} does not identify a managed release"
                )

            if not dep.unmanaged:
                return (
                    ref,
                    PackageNamespaceVersionDependency(
                        namespace=namespace,
                        version=release.name,
                        package_name=package_name,
                    ),
                )
            else:
                return ref, None
        except NotFoundError:
            raise DependencyResolutionError(f"No release found for tag {dep.tag}")


class GitHubReleaseTagResolver(Resolver):
    """Resolver that identifies a ref by finding the latest GitHub release."""

    name = "GitHub Release Resolver"
    include_beta = False

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, GitHubDynamicDependency)

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        repo = get_repo(dep.github, context)
        release = find_latest_release(repo, include_beta=self.include_beta)
        if release:
            ref = repo.tag(repo.ref(f"tags/{release.tag_name}").object.sha).object.sha
            package_config = get_remote_project_config(repo, ref)
            package_name, namespace = get_package_data(package_config)

            return (
                ref,
                PackageNamespaceVersionDependency(
                    namespace=namespace, version=release.name, package_name=package_name
                ),
            )

        return (None, None)


class GitHubBetaReleaseTagResolver(GitHubReleaseTagResolver):
    """Resolver that identifies a ref by finding the latest GitHub release, including betas."""

    name = "GitHub Release Resolver (Betas)"
    include_beta = True


class GitHubUnmanagedHeadResolver(Resolver):
    """Resolver that identifies a ref by finding the latest commit on the main branch."""

    name = "GitHub Unmanaged Resolver"

    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        return isinstance(dep, GitHubDynamicDependency)

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        repo = get_repo(dep.github, context)
        return (repo.branch(repo.default_branch).commit.sha, None)


class GitHubReleaseBranchResolver(Resolver, abc.ABC):
    """Abstract base class for resolvers that use release branches to find refs."""

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

    def locate_2gp_package_id(self, remote_repo, release_branch, context_2gp):
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
                break

        return version_id, commit


class GitHubReleaseBranch2GPResolver(GitHubReleaseBranchResolver):
    """Resolver that identifies a ref by finding a 2GP package version
    in a commit status on a `feature/NNN` release branch."""

    name = "GitHub Release Branch 2GP Resolver"
    branch_depth = 1

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
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
                f"Could not find feature branch prefix or 2GP context for {repo.clone_url}. Unable to resolve 2GP packages."
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
            version_id, commit = self.locate_2gp_package_id(
                repo,
                release_branch,
                remote_2gp_context,
            )

            if version_id:
                context.logger.info(
                    f"Located 2GP package version {version_id} for release {release_id} on {repo.clone_url} at commit {release_branch.commit.sha}"
                )
                package_config = get_remote_project_config(repo, commit.sha)
                package_name, _ = get_package_data(package_config)

                return commit.sha, PackageVersionIdDependency(
                    version_id=version_id, package_name=package_name
                )

        context.logger.warn(
            f"No 2GP package version located for release {release_id} on {repo.clone_url}."
        )
        return (None, None)


class GitHubPreviousReleaseBranch2GPResolver(GitHubReleaseBranch2GPResolver):
    """Resolver that identifies a ref by finding a 2GP package version
    in a commit status on a `feature/NNN` release branch that is earlier
    than the matching local release branch."""

    name = "GitHub Previous Release Branch 2GP Resolver"
    branch_depth = 3


class GitHubReleaseBranchExactMatch2GPResolver(GitHubReleaseBranchResolver):
    """Resolver that identifies a ref by finding a 2GP package version
    in a commit status on a branch whose name matches the local branch."""

    name = "GitHub Exact-Match 2GP Resolver"

    def resolve(
        self, dep: GitHubDynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        release_id = self.get_release_id(context)

        repo = context.get_repo_from_url(dep.github)
        if not repo:
            raise DependencyResolutionError(f"Unable to access repository {dep.github}")

        try:
            remote_branch_prefix = find_repo_feature_prefix(repo)
            remote_2gp_context = find_repo_2gp_context(repo)
        except Exception:
            context.logger.info(
                f"Could not find feature branch prefix or 2GP context for {repo.clone_url}. Unable to resolve 2GP packages."
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

        version_id, commit = self.locate_2gp_package_id(
            repo,
            release_branch,
            remote_2gp_context,
        )

        if version_id:
            context.logger.info(
                f"Located 2GP package version {version_id} for release {release_id} on {repo.clone_url} at commit {release_branch.commit.sha}"
            )

            package_config = get_remote_project_config(repo, commit.sha)
            package_name, _ = get_package_data(package_config)

            return commit.sha, PackageVersionIdDependency(
                version_id=version_id, package_name=package_name
            )

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


def get_static_dependencies(
    dependencies: List[Dependency],
    strategies: List[DependencyResolutionStrategy],
    context: BaseProjectConfig,
    ignore_deps: List[dict] = None,
):
    """Resolves the project__dependencies section of cumulusci.yml
    to convert dynamic GitHub dependencies into static dependencies
    by inspecting the referenced repositories.

    Keyword arguments:
    :param dependencies: a list of dependencies to resolve
    :param ignore_deps: if provided, ignore the specified dependencies wherever found.
    """

    while any(not d.is_flattened or not d.is_resolved for d in dependencies):
        for d in dependencies:
            if not d.is_resolved:
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
                        d.flatten(context)
                        for d in dependencies
                        if not _should_ignore_dependency(d, ignore_deps or [])
                    )
                ),
            )
        )

    # Make sure, if we had no flattening or resolving to do, that we apply the ignore list.
    return [
        d for d in dependencies if not _should_ignore_dependency(d, ignore_deps or [])
    ]


def _should_ignore_dependency(dependency: Dependency, ignore_deps: List[dict]):
    if not ignore_deps:
        return False

    ignore_github = [d["github"] for d in ignore_deps if "github" in d]
    ignore_namespace = [d["namespace"] for d in ignore_deps if "namespace" in d]

    if (
        isinstance(dependency, PackageNamespaceVersionDependency)
        and dependency.namespace
    ):
        return dependency.namespace in ignore_namespace
    if isinstance(dependency, GitHubDynamicDependency) and dependency.github:
        return dependency.github in ignore_github

    return False
