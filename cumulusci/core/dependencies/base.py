import contextlib
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import List, Optional, Tuple
from zipfile import ZipFile

from pydantic import AnyUrl

from cumulusci.core.config import OrgConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.core.sfdx import (
    SourceFormat,
    convert_sfdx_source,
    get_source_format_for_zipfile,
)
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder
from cumulusci.utils import temporary_dir
from cumulusci.utils.yaml.model_parser import HashableBaseModel
from cumulusci.utils.ziputils import zip_subfolder


class DependencyPin(HashableBaseModel, ABC):
    @abstractmethod
    def can_pin(self, d: "DynamicDependency") -> bool:
        ...

    @abstractmethod
    def pin(self, d: "DynamicDependency", context: BaseProjectConfig):
        ...


DependencyPin.update_forward_refs()


class Dependency(HashableBaseModel, ABC):
    """Abstract base class for models representing dependencies

    Dependencies can be _resolved_ to an immutable version, or not.
    They can also be _flattened_ (turned into a list including their own transitive dependencies) or not.
    """

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    def description(self):
        return self.name

    @property
    @abstractmethod
    def is_resolved(self):
        return False

    @property
    @abstractmethod
    def is_flattened(self):
        return False

    def flatten(self, context: BaseProjectConfig) -> List["Dependency"]:
        """Get a list including this dependency as well as its transitive dependencies."""
        return [self]

    def __str__(self):
        return self.description


Dependency.update_forward_refs()


class StaticDependency(Dependency, ABC):
    """Abstract base class for dependencies that we know how to install (i.e., they
    are already both resolved and flattened)."""

    @abstractmethod
    def install(self, org_config: OrgConfig, retry_options: Optional[dict] = None):
        pass

    @property
    def is_resolved(self):
        return True

    @property
    def is_flattened(self):
        return True


class DynamicDependency(Dependency, ABC):
    """Abstract base class for dependencies with dynamic references, like GitHub.
    These dependencies must be resolved and flattened before they can be installed."""

    url: Optional[AnyUrl] = None
    package_dependency: Optional[StaticDependency] = None
    password_env_name: Optional[str] = None
    vcs: str = ""

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


class UnmanagedDependency(StaticDependency, ABC):
    """Abstract base class for static, unmanaged dependencies."""

    unmanaged: Optional[bool] = None
    subfolder: Optional[str] = None
    namespace_inject: Optional[str] = None
    namespace_strip: Optional[str] = None
    collision_check: Optional[bool] = None

    def _get_unmanaged(self, org: OrgConfig):
        if self.unmanaged is None:
            if self.namespace_inject:
                return self.namespace_inject not in org.installed_packages
            else:
                return True

        return self.unmanaged

    @abstractmethod
    def _get_zip_src(self, context: BaseProjectConfig) -> ZipFile:
        pass

    def get_metadata_package_zip_builder(
        self, project_config: BaseProjectConfig, org: OrgConfig
    ) -> MetadataPackageZipBuilder:
        zip_src = self._get_zip_src(project_config)
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
                    convert_sfdx_source(self.subfolder, None, project_config.logger)
                )
                zip_src = None  # Don't use the zipfile if we converted source.

            context = TaskContext(org, project_config, project_config.logger)
            # We now know what to send to MetadataPackageZipBuilder
            # Note that subfolder logic is applied either by subsetting the zip
            # (for MDAPI) or by the conversion (for SFDX format)

            package_zip = MetadataPackageZipBuilder.from_zipfile(
                zip_src,
                path=real_path,
                options=options,
                context=context,
            )

        return package_zip

    def install(self, context: BaseProjectConfig, org: OrgConfig):

        context.logger.info(f"Deploying unmanaged metadata from {self.description}")

        package_zip_builder = self.get_metadata_package_zip_builder(context, org)
        task = TaskContext(
            org_config=org, project_config=context, logger=context.logger
        )
        api = ApiDeploy(task, package_zip_builder.as_base64())

        return api()


class DependencyResolutionStrategy(StrEnum):
    """Enum that defines a strategy for resolving a dynamic dependency into a static dependency."""

    STATIC_TAG_REFERENCE = "tag"
    COMMIT_STATUS_EXACT_BRANCH = "commit_status_exact_branch"
    COMMIT_STATUS_RELEASE_BRANCH = "commit_status_release_branch"
    COMMIT_STATUS_PREVIOUS_RELEASE_BRANCH = "commit_status_previous_release_branch"
    COMMIT_STATUS_DEFAULT_BRANCH = "commit_status_default_branch"
    UNLOCKED_EXACT_BRANCH = "unlocked_exact_branch"
    UNLOCKED_RELEASE_BRANCH = "unlocked_release_branch"
    UNLOCKED_PREVIOUS_RELEASE_BRANCH = "unlocked_previous_release_branch"
    UNLOCKED_DEFAULT_BRANCH = "unlocked_default_branch"
    BETA_RELEASE_TAG = "latest_beta"
    RELEASE_TAG = "latest_release"
    UNMANAGED_HEAD = "unmanaged"


class AbstractResolver(ABC):
    """Abstract base class for dependency resolution strategies."""

    name = "Resolver"

    @abstractmethod
    def can_resolve(self, dep: DynamicDependency, context: BaseProjectConfig) -> bool:
        pass

    @abstractmethod
    def resolve(
        self, dep: DynamicDependency, context: BaseProjectConfig
    ) -> Tuple[Optional[str], Optional[StaticDependency]]:
        pass

    def __str__(self):
        return self.name
