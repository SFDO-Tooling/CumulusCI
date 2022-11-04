import abc
import contextlib
import itertools
import logging
import os
from typing import List, Optional
from zipfile import ZipFile

import pydantic
from github3.exceptions import NotFoundError
from github3.repos.repo import Repository
from pydantic.networks import AnyUrl

from cumulusci.core.config import OrgConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.github import (
    get_package_data,
    get_remote_project_config,
    get_repo,
)
from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.core.exceptions import DependencyParseError, DependencyResolutionError
from cumulusci.core.sfdx import (
    SourceFormat,
    convert_sfdx_source,
    get_source_format_for_zipfile,
)
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    PackageInstallOptions,
    install_package_by_namespace_version,
    install_package_by_version_id,
)
from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder
from cumulusci.utils import (
    download_extract_github_from_repo,
    download_extract_zip,
    temporary_dir,
)
from cumulusci.utils.yaml.model_parser import HashableBaseModel
from cumulusci.utils.ziputils import zip_subfolder

logger = logging.getLogger(__name__)


def _validate_github_parameters(values):
    if values.get("repo_owner") or values.get("repo_name"):
        logger.warning(
            "The repo_name and repo_owner keys are deprecated. Please use the github key."
        )

    assert values.get("github") or (
        values.get("repo_owner") and values.get("repo_name")
    ), "Must specify `github` or `repo_owner` and `repo_name`"

    # Populate the `github` property if not already populated.
    if not values.get("github") and values.get("repo_name"):
        values[
            "github"
        ] = f"https://github.com/{values['repo_owner']}/{values['repo_name']}"
        values.pop("repo_owner")
        values.pop("repo_name")

    return values


class DependencyPin(HashableBaseModel, abc.ABC):
    @abc.abstractmethod
    def can_pin(self, d: "DynamicDependency") -> bool:
        ...

    @abc.abstractmethod
    def pin(self, d: "DynamicDependency", context: BaseProjectConfig):
        ...


DependencyPin.update_forward_refs()


class GitHubDependencyPin(DependencyPin):
    """Model representing a request to pin a GitHub dependency to a specific tag"""

    github: str
    tag: str

    def can_pin(self, d: "DynamicDependency") -> bool:
        return isinstance(d, BaseGitHubDependency) and d.github == self.github

    def pin(self, d: "BaseGitHubDependency", context: BaseProjectConfig):
        from cumulusci.core.dependencies.resolvers import (  # Circular imports
            GitHubTagResolver,
        )

        if d.tag and d.tag != self.tag:
            raise DependencyResolutionError(
                f"A pin is specified for {self.github}, but the dependency already has a tag specified."
            )
        d.tag = self.tag
        d.ref, d.package_dependency = GitHubTagResolver().resolve(d, context)


GitHubDependencyPin.update_forward_refs()


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
    def description(self):
        return self.name

    @property
    @abc.abstractmethod
    def is_resolved(self):
        return False

    @property
    @abc.abstractmethod
    def is_flattened(self):
        return False

    def flatten(self, context: BaseProjectConfig) -> List["Dependency"]:
        """Get a list including this dependency as well as its transitive dependencies."""
        return [self]

    def __str__(self):
        return self.description


Dependency.update_forward_refs()


class StaticDependency(Dependency, abc.ABC):
    """Abstract base class for dependencies that we know how to install (i.e., they
    are already both resolved and flattened)."""

    @abc.abstractmethod
    def install(self, org_config: OrgConfig, retry_options: Optional[dict] = None):
        pass

    @property
    def is_resolved(self):
        return True

    @property
    def is_flattened(self):
        return True


class DynamicDependency(Dependency, abc.ABC):
    """Abstract base class for dependencies with dynamic references, like GitHub.
    These dependencies must be resolved and flattened before they can be installed."""

    package_dependency: Optional[StaticDependency] = None
    password_env_name: Optional[str] = None

    @property
    def is_flattened(self):
        return False

    def resolve(
        self,
        context: BaseProjectConfig,
        strategies: List,  # List[DependencyResolutionStrategy], but circular import
        pins: Optional[List[DependencyPin]] = None,
    ):
        """Resolve a DynamicDependency that is not pinned to a specific version into one that is."""
        # avoid import cycle
        from .resolvers import resolve_dependency

        for pin in pins or []:
            if pin.can_pin(self):
                context.logger.info(f"Pinning dependency {self} to {pin}")
                pin.pin(self, context)
                return

        resolve_dependency(self, context, strategies)


class BaseGitHubDependency(DynamicDependency, abc.ABC):
    """Base class for dynamic dependencies that reference a GitHub repo."""

    pin_class = GitHubDependencyPin

    github: Optional[AnyUrl] = None

    repo_owner: Optional[str] = None  # Deprecated - use full URL
    repo_name: Optional[str] = None  # Deprecated - use full URL

    tag: Optional[str] = None
    ref: Optional[str] = None

    @property
    @abc.abstractmethod
    def is_unmanaged(self):
        pass

    @property
    def is_resolved(self):
        return bool(self.ref)

    @pydantic.root_validator
    def check_deprecated_fields(cls, values):
        if values.get("repo_owner") or values.get("repo_name"):
            logger.warning(
                "The dependency keys `repo_owner` and `repo_name` are deprecated. Use the full repo URL with the `github` key instead."
            )
        return values

    @pydantic.root_validator
    def check_complete(cls, values):
        assert values["ref"] is None, "Must not specify `ref` at creation."

        return _validate_github_parameters(values)

    @property
    def name(self):
        return f"Dependency: {self.github}"


class GitHubDynamicSubfolderDependency(BaseGitHubDependency):
    """A dependency expressed by a reference to a subfolder of a GitHub repo, which needs
    to be resolved to a specific ref. This is always an unmanaged dependency."""

    subfolder: str
    namespace_inject: Optional[str] = None
    namespace_strip: Optional[str] = None

    @property
    def is_unmanaged(self):
        return True

    def flatten(self, context: BaseProjectConfig) -> List[Dependency]:
        """Convert to a static dependency after resolution"""

        if not self.is_resolved:
            raise DependencyResolutionError(
                f"Dependency {self} is not resolved and cannot be flattened."
            )

        return [
            UnmanagedGitHubRefDependency(
                github=self.github,
                ref=self.ref,
                subfolder=self.subfolder,
                namespace_inject=self.namespace_inject,
                namespace_strip=self.namespace_strip,
            )
        ]

    @property
    def name(self):
        return f"Dependency: {self.github}/{self.subfolder}"

    @property
    def description(self):
        loc = f" @{self.tag or self.ref}" if self.ref or self.tag else ""
        return f"{self.github}/{self.subfolder}{loc}"


class GitHubDynamicDependency(BaseGitHubDependency):
    """A dependency expressed by a reference to a GitHub repo, which needs
    to be resolved to a specific ref and/or package version."""

    unmanaged: bool = False
    namespace_inject: Optional[str] = None
    namespace_strip: Optional[str] = None
    password_env_name: Optional[str] = None

    skip: List[str] = []

    @property
    def is_unmanaged(self):
        return self.unmanaged

    @pydantic.validator("skip", pre=True)
    def listify_skip(cls, v):
        if v and not isinstance(v, list):
            v = [v]
        return v

    @pydantic.root_validator
    def check_unmanaged_values(cls, values):
        if not values.get("unmanaged") and (
            values.get("namespace_inject") or values.get("namespace_strip")
        ):
            raise ValueError(
                "The namespace_strip and namespace_inject fields require unmanaged = True"
            )

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
            for dirname in sorted(contents.keys()):
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
        if not self.is_resolved:
            raise DependencyResolutionError(
                f"Dependency {self} is not resolved and cannot be flattened."
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
                    f"Unable to flatten dependency {self} because a transitive dependency could not be parsed."
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

        if not self.package_dependency:
            if managed:
                # We had an expectation of finding a package version and did not.
                raise DependencyResolutionError(
                    f"Could not find latest release for {self}"
                )

            # Deploy the project, if unmanaged.
            deps.append(
                UnmanagedGitHubRefDependency(
                    github=self.github,
                    ref=self.ref,
                    unmanaged=self.unmanaged,
                    namespace_inject=self.namespace_inject,
                    namespace_strip=self.namespace_strip,
                )
            )
        else:
            deps.append(self.package_dependency)

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
    def description(self):
        unmanaged = " (unmanaged)" if self.unmanaged else ""
        loc = f" @{self.tag or self.ref}" if self.ref or self.tag else ""
        return f"{self.github}{unmanaged}{loc}"


class PackageNamespaceVersionDependency(StaticDependency):
    """Static dependency on a package identified by namespace and version number."""

    namespace: str
    version: str
    package_name: Optional[str] = None
    version_id: Optional[str] = None

    password_env_name: Optional[str] = None

    @property
    def package(self):
        return self.package_name or self.namespace or "Unknown Package"

    def install(
        self,
        context: BaseProjectConfig,
        org: OrgConfig,
        options: Optional[PackageInstallOptions] = None,
        retry_options=None,
    ):
        if not options:
            options = PackageInstallOptions()
        if self.password_env_name:
            options.password = os.environ.get(self.password_env_name)
        if not retry_options:
            retry_options = DEFAULT_PACKAGE_RETRY_OPTIONS

        if "Beta" in self.version:
            version_string = self.version.split(" ")[0]
            beta = self.version.split(" ")[-1].strip(")")
            version = f"{version_string}b{beta}"
        else:
            version = self.version

        if org.has_minimum_package_version(
            self.namespace,
            version,
        ):
            context.logger.info(
                f"{self} or a newer version is already installed; skipping."
            )
            return

        context.logger.info(f"Installing {self.description}")
        install_package_by_namespace_version(
            context,
            org,
            self.namespace,
            self.version,
            options,
            retry_options=retry_options,
        )

    @property
    def name(self):
        return f"Install {self.package} {self.version}"

    @property
    def description(self):
        return f"{self.package} {self.version}"


class PackageVersionIdDependency(StaticDependency):
    """Static dependency on a package identified by 04t version id."""

    version_id: str
    package_name: Optional[str] = None
    version_number: Optional[str] = None

    password_env_name: Optional[str] = None

    @property
    def package(self):
        return self.package_name or "Unknown Package"

    def install(
        self,
        context: BaseProjectConfig,
        org: OrgConfig,
        options: Optional[PackageInstallOptions] = None,
        retry_options=None,
    ):
        if not options:
            options = PackageInstallOptions()
        if self.password_env_name:
            options.password = os.environ.get(self.password_env_name)
        if not retry_options:
            retry_options = DEFAULT_PACKAGE_RETRY_OPTIONS

        if any(
            self.version_id == v.id
            for v in itertools.chain(*org.installed_packages.values())
        ):
            context.logger.info(
                f"{self} or a newer version is already installed; skipping."
            )
            return

        context.logger.info(f"Installing {self.description}")
        install_package_by_version_id(
            context,
            org,
            self.version_id,
            options,
            retry_options=retry_options,
        )

    @property
    def name(self):
        return f"Install {self.description}"

    @property
    def description(self):
        return f"{self.package} {self.version_number or self.version_id}"


class UnmanagedDependency(StaticDependency, abc.ABC):
    """Abstract base class for static, unmanaged dependencies."""

    unmanaged: Optional[bool] = None
    subfolder: Optional[str] = None
    namespace_inject: Optional[str] = None
    namespace_strip: Optional[str] = None

    def _get_unmanaged(self, org: OrgConfig):
        if self.unmanaged is None:
            if self.namespace_inject:
                return self.namespace_inject not in org.installed_packages
            else:
                return True

        return self.unmanaged

    @abc.abstractmethod
    def _get_zip_src(self, context: BaseProjectConfig) -> ZipFile:
        pass

    def get_metadata_package_zip_builder(
        self, context: BaseProjectConfig, org: OrgConfig
    ) -> MetadataPackageZipBuilder:
        zip_src = self._get_zip_src(context)
        # Determine whether to inject namespace prefixes or not
        # If and only if we have no explicit configuration.

        options = {
            "unmanaged": self._get_unmanaged(org),
            "namespace_inject": self.namespace_inject,
            "namespace_strip": self.namespace_strip,
        }

        # We have a zip file. Now, determine how to handle
        # MDAPI/SFDX format, with or without a subfolder specified.

        # In only two cases do we need to do a zip subset.
        # Either we have a repo root in MDAPI format and need to get `src`,
        # or we're deploying a subfolder that is in MDAPI format.
        zip_extract_subfolder = None
        if (
            not self.subfolder
            and get_source_format_for_zipfile(zip_src, "src") is SourceFormat.MDAPI
        ):
            zip_extract_subfolder = "src"
        elif (
            self.subfolder
            and get_source_format_for_zipfile(zip_src, self.subfolder)
            is SourceFormat.MDAPI
        ):
            zip_extract_subfolder = self.subfolder

        if zip_extract_subfolder:
            zip_src = zip_subfolder(zip_src, zip_extract_subfolder)

        source_format = get_source_format_for_zipfile(
            zip_src, self.subfolder if not zip_extract_subfolder else None
        )

        real_path = None
        package_zip = None
        with contextlib.ExitStack() as stack:
            if source_format is SourceFormat.SFDX:
                # Convert source first.
                stack.enter_context(temporary_dir(chdir=True))
                zip_src.extractall()
                real_path = stack.enter_context(
                    convert_sfdx_source(self.subfolder, None, context.logger)
                )
                zip_src = None  # Don't use the zipfile if we converted source.

            # We now know what to send to MetadataPackageZipBuilder
            # Note that subfolder logic is applied either by subsetting the zip
            # (for MDAPI) or by the conversion (for SFDX format)

            package_zip = MetadataPackageZipBuilder.from_zipfile(
                zip_src,
                path=real_path,
                options=options,
                logger=context.logger,
            )

        return package_zip

    def install(self, context: BaseProjectConfig, org: OrgConfig):

        context.logger.info(f"Deploying unmanaged metadata from {self.description}")

        package_zip_builder = self.get_metadata_package_zip_builder(context, org)
        task = TaskContext(org_config=org, project_config=context, logger=logger)
        api = ApiDeploy(task, package_zip_builder.as_base64())

        return api()


class UnmanagedGitHubRefDependency(UnmanagedDependency):
    """Static dependency on unmanaged metadata in a specific GitHub ref and subfolder."""

    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None

    # or
    github: Optional[AnyUrl] = None

    # and
    ref: str

    # for backwards compatibility only; currently unused
    filename_token: Optional[str] = None
    namespace_token: Optional[str] = None

    @pydantic.root_validator
    def validate(cls, values):
        return _validate_github_parameters(values)

    def _get_zip_src(self, context):
        repo = get_repo(self.github, context)

        # We don't pass `subfolder` to download_extract_github_from_repo()
        # because we need to get the whole ref in order to
        # correctly handle any permutation of MDAPI/SFDX format,
        # with or without a subfolder specified.

        # install() will take care of that for us.
        return download_extract_github_from_repo(
            repo,
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
        subfolder = (
            f"/{self.subfolder}" if self.subfolder and self.subfolder != "src" else ""
        )

        return f"{self.github}{subfolder} @{self.ref}"


class UnmanagedZipURLDependency(UnmanagedDependency):
    """Static dependency on unmanaged metadata downloaded as a zip file from a URL."""

    zip_url: AnyUrl

    def _get_zip_src(self, context: BaseProjectConfig):
        # We don't pass `subfolder` to download_extract_github_from_repo()
        # because we need to get the whole ref in order to
        # correctly handle any permutation of MDAPI/SFDX format,
        # with or without a subfolder specified.

        # install() will take care of that for us.

        return download_extract_zip(self.zip_url)

    @property
    def name(self):
        subfolder = f"/{self.subfolder}" if self.subfolder else ""
        return f"Deploy {self.zip_url} {subfolder}"

    @property
    def description(self):
        subfolder = f"/{self.subfolder}" if self.subfolder else ""
        return f"{self.zip_url} {subfolder}"


def parse_pins(pins: Optional[List[dict]]) -> List[DependencyPin]:
    """Convert a list of dependency pin specifications in the form of dicts
    (as defined in `cumulusci.yml`) and parse each into a concrete DependencyPin subclass.

    Throws DependencyParseError if a dict cannot be parsed."""
    parsed_pins = []
    for pin in pins or []:
        parsed = parse_dependency_pin(pin)
        if parsed is None:
            raise DependencyParseError(f"Unable to parse dependency pin: {pin}")
        parsed_pins.append(parsed)

    return parsed_pins


AVAILABLE_DEPENDENCY_PIN_CLASSES = [GitHubDependencyPin]


def parse_dependency_pin(pin_dict: dict) -> Optional[DependencyPin]:
    """Parse a single dependency pin specification in the form of a dict
    into a concrete DependencyPin subclass.

    Returns None if the given dict cannot be parsed."""

    for dependency_pin_class in AVAILABLE_DEPENDENCY_PIN_CLASSES:
        try:
            pin = dependency_pin_class.parse_obj(pin_dict)
            if pin:
                return pin
        except pydantic.ValidationError:
            pass


def parse_dependencies(deps: Optional[List[dict]]) -> List[Dependency]:
    """Convert a list of dependency specifications in the form of dicts
    (as defined in `cumulusci.yml`) and parse each into a concrete Dependency subclass.

    Throws DependencyParseError if a dict cannot be parsed."""
    parsed_deps = []
    for dep in deps or []:
        parsed = parse_dependency(dep)
        if parsed is None:
            raise DependencyParseError(f"Unable to parse dependency: {dep}")
        parsed_deps.append(parsed)
    return parsed_deps


AVAILABLE_DEPENDENCY_CLASSES = [
    PackageVersionIdDependency,
    PackageNamespaceVersionDependency,
    UnmanagedGitHubRefDependency,
    UnmanagedZipURLDependency,
    GitHubDynamicDependency,
    GitHubDynamicSubfolderDependency,
]


def parse_dependency(dep_dict: dict) -> Optional[Dependency]:
    """Parse a single dependency specification in the form of a dict
    into a concrete Dependency subclass.

    Returns None if the given dict cannot be parsed."""

    # The order in which we attempt parsing is significant.
    # GitHubDynamicDependency has an optional `ref` field, but we want
    # any dependencies with a populated `ref` to be parsed as static deps.

    # We also want PackageVersionIdDependency to match before
    # PackageNamespaceVersionDependency, which can also accept a `version_id`.

    for dependency_class in AVAILABLE_DEPENDENCY_CLASSES:
        try:
            dep = dependency_class.parse_obj(dep_dict)
            if dep:
                return dep
        except pydantic.ValidationError:
            pass
