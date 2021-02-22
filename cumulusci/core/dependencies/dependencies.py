import abc
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.salesforce_api.package_install import install_package_version
import io

from github3.exceptions import NotFoundError
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load

from github3.repos.repo import Repository
from cumulusci.core.dependencies.resolvers import (
    DependencyResolutionStrategy,
    get_resolver,
)
import pydantic
from cumulusci.core.exceptions import DependencyResolutionError
from typing import Optional, List
from pydantic import BaseModel
from cumulusci.core.config import OrgConfig
from cumulusci.core.config.project_config import BaseProjectConfig


class Dependency(BaseModel, abc.ABC):
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
    def install(self, org_config: OrgConfig):
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


class GitHubDynamicReleaseType(str, Enum):
    previous = "previous"
    latest_beta = "latest_beta"
    latest = "latest"


class GitHubDynamicDependency(DynamicDependency):
    github: Optional[str]
    release: Optional[
        GitHubDynamicReleaseType
    ]  # TODO: implement. Is this supported on deps or only on sources?

    unmanaged: bool = False
    subfolder: Optional[str]
    # Do we need the namespace injection ones here too? YES.

    tag: Optional[str]
    # QUESTION: can a `tag` specifier identify a managed release or just a ref for unmanaged?
    ref: Optional[str]

    repo_owner: Optional[str]  # This should be deprecated as it's GitHub-specific
    repo_name: Optional[str]  # This should be deprecated as it's GitHub-specific

    dependencies: Optional[
        List[dict]
    ]  # How do we handle this? Is it legal for subdeps to be
    # listed in YAML, or is this only created during resolution?
    skip: List[str] = []

    # UI options
    name: Optional[str]  # Can this be inferred? Is it ever specified in YAML?

    @property
    def is_resolved(self):
        return self.ref is not None

    @pydantic.root_validator
    def check_deprecations(cls, values):
        pass  # TODO

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

        # Populate the `github` property if not already populated.
        if not values.get("github"):
            values[
                "github"
            ] = f"https://github.com/{values['repo_owner']}/{values['repo_name']}"

    def get_repo(self, context: BaseProjectConfig) -> Repository:
        repo = context.get_github_repo(self.github)  # TODO: handle owner/name.
        if repo is None:
            raise DependencyResolutionError(
                f"Github repository {self.github} not found or not authorized."
            )

        return repo

    def _flatten_unpackaged(
        self,
        repo: Repository,
        subfolder: str,
        skip: List[str],
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

                name = f"Deploy {subfolder}"

                unpackaged.append(
                    UnmanagedDependency(
                        name=name,
                        repo_url=self.github,
                        ref=self.ref,
                        subfolder=subfolder,
                        unmanaged=self.unmanaged,
                        namespace_inject=self.namespace_inject,
                        namespace_strip=self.namespace_strip,
                    )
                )

        return unpackaged

    def flatten(self, context: BaseProjectConfig) -> List[Dependency]:
        if not self.is_resolved:
            raise DependencyResolutionError(
                f"Dependency {self.github} is not resolved and cannot be flattened."
            )

        deps = []

        # TODO: have validators populate self.github
        context.logger.info(f"Collecting dependencies from Github repo {self.github}")

        # TODO: implement skipping.
        skip = self.skip
        if not isinstance(skip, list):
            skip = [skip]

        repo = self.get_repo(context)

        # Get the cumulusci.yml file
        contents = repo.file_contents("cumulusci.yml", ref=self.ref)
        cumulusci_yml = cci_safe_load(io.StringIO(contents.decoded.decode("utf-8")))

        # Get the namespace from the cumulusci.yml if set
        package_config = cumulusci_yml.get("project", {}).get("package", {})
        namespace = package_config.get("namespace")
        package_name = (
            package_config.get("name_managed")
            or package_config.get("name")
            or namespace
        )

        # Parse upstream dependencies from the repo's cumulusci.yml
        # These may be unresolved or unflattened; if so, `get_static_dependencies()`
        # will manage them.
        project = cumulusci_yml.get("project", {})
        dependencies = project.get("dependencies")
        if dependencies:
            deps.extend([parse_dependency(d) for d in dependencies])
            if None in deps:
                raise DependencyResolutionError("Unable to flatten dependency")

        # Check for unmanaged flag on a namespaced package
        unmanaged = namespace and self.unmanaged is True

        # Look for subfolders under unpackaged/pre
        deps.extend(self._flatten_unpackaged(repo, "unpackaged/pre", skip=skip))

        # Look for metadata under src (deployed if no namespace)
        if unmanaged or not namespace:
            contents = repo.directory_contents("src", ref=ref)
            if contents:
                deps.append(
                    UnmanagedDependency(
                        name=f"Deploy {package_name or repo_name}",
                        repo_url=self.github,
                        ref=self.ref,
                        subfolder="src",  # TODO: support SFDX format unmanaged deps.
                        unmanaged=self.unmanaged,
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

        # By default, we always inject the project's namespace into
        # unpackaged/post metadata
        deps.extend(
            self._flatten_unpackaged(
                repo,
                "unpackaged/post",
                skip,
                namespace_inject=namespace,
                unmanaged=unmanaged,
            )
        )

        return deps

        # if namespace and not dependency.get("namespace_inject"):
        #     dependency["namespace_inject"] = namespace
        #     dependency["unmanaged"] = unmanaged


class ManagedPackageInstallOptions(BaseModel):
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
        return self.package_name or self.namespace

    @property
    def step_name(self):
        return (
            f"Install {self.package} version {self.package_version_id or self.version}"
        )

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
        if self.namespace:
            context.logger.info(
                "Installing {} version {}".format(self.namespace, self.version)
            )
            # TODO: retries.
            package_zip = InstallPackageZipBuilder(
                self.namespace,
                self.version,
                securityType=options.security_type,
            )()

            api = self.api_class(
                self,
                package_zip,
                purge_on_delete=options.purge_on_delete,  # Does this mean anything for MP installs?
            )
            api()
        elif self.package_version_id:
            context.logger.info(f"Installing {self.package_version_id}")
            # TODO: retries
            install_package_version(context, org, self.package_version_id, options)


class UnmanagedDependency(
    StaticDependency
):  # TODO: this might not be a static dep if `ref` is not specified. Make GitHubDynamicDependency handle those with repo_url - or did we innovate that here?
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
    namespace_strip: Optional[str]  # Should this be deprecated?

    @pydantic.root_validator
    def validate(cls, values):
        if "repo_name" in values or "repo_owner" in values:
            logger.warn(
                "The repo_name and repo_owner keys are deprecated. Please use repo_url."
            )

        assert (
            "zip_url" in values
            or ("repo_url" in values and "ref" in values)
            or ("repo_name" in values and "repo_owner" in values and "ref" in values)
        ), "Must specify `zip_url`, or `repo_url` and `ref`"

        # TODO: populate repo_url given repo_name and repo_owner.

    def install(self, context: BaseProjectConfig, org: OrgConfig):
        zip_src = None
        if self.zip_url:
            context.logger.info(
                f"Deploying unmanaged metadata from /{self.subfolder} of {self.zip_url}"
            )
            zip_src = self._download_extract_zip(self.zip_url, subfolder=self.subfolder)
        elif self.repo_url:
            context.logger.info(
                f"Deploying unmanaged metadata from /{self.subfolder} of {self.repo_url}"
            )
            repo = self.get_repo()

            zip_src = self._download_extract_github(
                repo,
                self.subfolder,
                ref=self.ref,
            )

        if zip_src:
            # determine whether to inject namespace prefixes or not
            options = dependency.copy()
            if "unmanaged" not in options:
                namespace = options.get("namespace_inject")
                options["unmanaged"] = (
                    not namespace
                ) or namespace not in self.org_config.installed_packages

            package_zip = MetadataPackageZipBuilder.from_zipfile(
                zip_src, options=options, logger=self.logger
            ).as_base64()
            # FIXME: install the zip


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
