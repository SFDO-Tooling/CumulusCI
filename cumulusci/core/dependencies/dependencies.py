import abc
import io
import logging
from typing import List, Optional

import pydantic
from github3.exceptions import NotFoundError
from github3.repos.repo import Repository
from pydantic import BaseModel
from pydantic.networks import AnyUrl

from cumulusci.core.config import OrgConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.resolvers import (
    DependencyResolutionStrategy,
    get_resolver,
)
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    install_1gp_package_version,
    install_package_version,
)
from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder
from cumulusci.utils import download_extract_github_from_repo, download_extract_zip
from cumulusci.utils.git import split_repo_url
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load

logger = logging.getLogger(__name__)


class HashableBaseModel(BaseModel):
    # See https://github.com/samuelcolvin/pydantic/issues/1303
    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))


class Dependency(HashableBaseModel, abc.ABC):
    @property
    @abc.abstractmethod
    def is_resolved(self):
        return False

    @property
    @abc.abstractmethod
    def is_flattened(self):
        return False

    def flatten(self, context: BaseProjectConfig) -> List["Dependency"]:
        return [self]

    def resolve(
        self, context: BaseProjectConfig, strategies: List[DependencyResolutionStrategy]
    ):
        pass


class StaticDependency(Dependency, abc.ABC):
    @abc.abstractmethod
    def install(self, org_config: OrgConfig, retry_options: dict = None):
        pass

    @property
    def is_resolved(self):
        return True

    @property
    def is_flattened(self):
        return True


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

            if resolver and resolver.can_resolve(self, context):
                try:
                    self.ref, self.managed_dependency = resolver.resolve(self, context)
                    if self.ref:
                        break
                except DependencyResolutionError:
                    context.logger.info(
                        f"Resolution strategy {s} failed for dependency {self}."
                    )

        if not self.ref:
            raise DependencyResolutionError(f"Unable to resolve dependency {self}")


class GitHubRepoMixin:
    def get_repo(self, context: BaseProjectConfig) -> Repository:
        repo = context.get_github_repo(self.github)
        if repo is None:
            raise DependencyResolutionError(
                f"Github repository {self.github} not found or not authorized."
            )

        return repo


class GitHubDynamicDependency(GitHubRepoMixin, DynamicDependency):
    github: Optional[AnyUrl]

    repo_owner: Optional[str]  # Deprecate - use full URL
    repo_name: Optional[str]  # Deprecate - use full URL

    unmanaged: bool = False
    subfolder: Optional[str]
    namespace_inject: Optional[str]
    namespace_strip: Optional[str]  # FIXME: Should this be deprecated?

    tag: Optional[str]
    ref: Optional[str]

    skip: List[str] = []

    # UI options
    name: Optional[
        str
    ]  # It's previously legal to specify this in YAML, but unclear if used.

    @property
    def is_resolved(self):
        return self.ref is not None

    @pydantic.root_validator
    def check_deprecations(cls, values):
        if "repo_owner" or "repo_name" in values:
            logger.warning(
                "The dependency keys `repo_owner` and `repo_name` are deprecated. Use `github` instead."
            )

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

        # Populate the `github` and `repo_name, `repo_owner` properties if not already populated.
        if not values.get("repo_name"):
            values["repo_owner"], values["repo_name"] = split_repo_url(values["github"])

        if not values.get("github"):
            values[
                "github"
            ] = f"https://github.com/{values['repo_owner']}/{values['repo_name']}"

    def _flatten_unpackaged(
        self,
        repo: Repository,
        subfolder: str,
        skip: List[str],
        managed: bool,
        namespace: Optional[str],
    ) -> List[StaticDependency]:
        unpackaged = []
        try:
            contents = repo.directory_contents(
                "unpackaged/pre", return_as=dict, ref=self.ref
            )
        except NotFoundError:
            contents = None

        if contents:
            for dirname in list(contents.keys()):
                subfolder = f"{subfolder}/{dirname}"
                if subfolder in skip:
                    continue

                unpackaged.append(
                    UnmanagedDependency(
                        repo_url=self.github,
                        ref=self.ref,
                        subfolder=subfolder,
                        unmanaged=not managed,
                        namespace_inject=namespace if namespace and managed else None,
                        namespace_strip=namespace
                        if namespace and not managed
                        else None,
                    )
                )

        return unpackaged

    def flatten(self, context: BaseProjectConfig) -> List[Dependency]:
        if not self.is_resolved:
            raise DependencyResolutionError(
                f"Dependency {self.github} is not resolved and cannot be flattened."
            )

        deps = []

        context.logger.info(f"Collecting dependencies from Github repo {self.github}")
        repo = self.get_repo(context)

        # TODO: handle subdependencies
        # They are allowed in cumulusci.yml, but should be deprecated or even removed now.

        # Get the cumulusci.yml file
        contents = repo.file_contents("cumulusci.yml", ref=self.ref)
        cumulusci_yml = cci_safe_load(io.StringIO(contents.decoded.decode("utf-8")))

        # Get the namespace from the cumulusci.yml if set
        # FIXME: this logic is duplicative with some in resolvers.
        # Can we unify?
        package_config = cumulusci_yml.get("project", {}).get("package", {})
        namespace = package_config.get("namespace")

        # Parse upstream dependencies from the repo's cumulusci.yml
        # These may be unresolved or unflattened; if so, `get_static_dependencies()`
        # will manage them.
        project = cumulusci_yml.get("project", {})
        dependencies = project.get("dependencies")
        if dependencies:
            deps.extend([parse_dependency(d) for d in dependencies])
            if None in deps:
                raise DependencyResolutionError(
                    "Unable to flatten dependency {self} because a transitive dependency could not be parsed."
                )

        # Check for unmanaged flag on a namespaced package
        managed = namespace and not self.unmanaged

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
                    UnmanagedDependency(
                        repo_url=self.github,
                        ref=self.ref,
                        subfolder="src",  # TODO: support SFDX format unmanaged deps.
                        unmanaged=self.unmanaged,
                        managed=False,
                        namespace=None,
                        namespace_inject=self.namespace_inject,
                        namespace_strip=self.namespace_strip,
                    )
                )
        else:
            if namespace:
                if self.managed_dependency is None:
                    raise DependencyResolutionError(
                        f"Could not find latest release for {namespace}"
                    )

                deps.append(self.managed_dependency)

        # We always inject the project's namespace into unpackaged/post metadata
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


class ManagedPackageInstallOptions(HashableBaseModel):
    activate_remote_site_settings: bool = True
    name_conflict_resolution: str = "Block"
    password: Optional[str]
    security_type: str = "FULL"


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
        return self.package_name or self.namespace or "Unknown Package"

    @property
    def step_name(self):
        return str(self)

    @pydantic.root_validator
    def validate(cls, values):
        assert (
            "namespace" in values and "version" in values
        ) or "package_version_id" in values, (
            "Must specify `namespace` and `version`, or `package_version_id`"
        )

    def install(
        self,
        context: BaseProjectConfig,
        org: OrgConfig,
        options: ManagedPackageInstallOptions = None,
    ):
        if not options:
            options = ManagedPackageInstallOptions()

        if self.namespace and self.version:
            context.logger.info(
                "Installing {} version {}".format(self.package, self.version)
            )
            install_1gp_package_version(
                context,
                org,
                self.namespace,
                self.version,
                options,
                retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
            )
        elif self.package_version_id:
            context.logger.info(f"Installing {self.package_version_id}")
            install_package_version(
                context,
                org,
                self.package_version_id,
                options,
                retry_options=DEFAULT_PACKAGE_RETRY_OPTIONS,
            )

    def __str__(self):
        return f"Dependency: {self.package} version {self.package_version_id or self.version}"


class UnmanagedDependency(GitHubRepoMixin, StaticDependency):
    zip_url: Optional[AnyUrl]

    # or
    repo_owner: Optional[str]
    repo_name: Optional[str]

    # or
    github: Optional[AnyUrl]

    # and
    ref: Optional[str]

    unmanaged: Optional[bool]
    subfolder: Optional[str]
    namespace_inject: Optional[str]
    namespace_strip: Optional[str]  # FIXME: Should this be deprecated?

    @pydantic.root_validator
    def validate(cls, values):
        if "repo_name" in values or "repo_owner" in values:
            logger.warn(
                "The repo_name and repo_owner keys are deprecated. Please use the github key."
            )

        assert (
            "zip_url" in values
            or ("github" in values and "ref" in values)
            or ("repo_name" in values and "repo_owner" in values and "ref" in values)
        ), "Must specify `zip_url`, or `github` and `ref`"

        # Populate the `github` and `repo_name, `repo_owner` properties if not already populated.
        if not values.get("repo_name"):
            values["repo_owner"], values["repo_name"] = split_repo_url(values["github"])

        if not values.get("github"):
            values[
                "github"
            ] = f"https://github.com/{values['repo_owner']}/{values['repo_name']}"

    def install(self, context: BaseProjectConfig, org: OrgConfig):
        zip_src = None
        if self.zip_url:
            context.logger.info(
                f"Deploying unmanaged metadata from /{self.subfolder} of {self.zip_url}"
            )
            zip_src = download_extract_zip(self.zip_url, subfolder=self.subfolder)
        elif self.github:
            context.logger.info(
                f"Deploying unmanaged metadata from /{self.subfolder} of {self.github} at {self.ref}"
            )
            repo = self.get_repo(context)

            zip_src = download_extract_github_from_repo(
                repo,
                self.subfolder,
                ref=self.ref,
            )

        if zip_src:
            # Determine whether to inject namespace prefixes or not
            namespace = self.namespace_inject
            options = {
                "unmanaged": self.unmanaged
                or ((not namespace) or namespace not in org.installed_packages),
                "namespace_inject": self.namespace_inject,
                "namespace_strip": self.namespace_strip,
            }

            package_zip = MetadataPackageZipBuilder.from_zipfile(
                zip_src, options=options, logger=logger
            ).as_base64()
            api = ApiDeploy(self, package_zip)
            return api()

    def __str__(self):
        subfolder = f"/{self.subfolder}" if self.subfolder else ""

        if self.github:
            return f"Dependency: {self.github} {subfolder} @{self.ref}"
        else:
            return f"Dependency: {self.zip_url} {subfolder}"


def parse_dependency(dep_dict: dict) -> Optional[Dependency]:
    for dependency_class in [
        ManagedPackageDependency,
        UnmanagedDependency,
        GitHubDynamicDependency,
    ]:
        try:
            dep = dependency_class.parse_obj(dep_dict)
            if dep:
                return dep
        except pydantic.ValidationError:
            pass
