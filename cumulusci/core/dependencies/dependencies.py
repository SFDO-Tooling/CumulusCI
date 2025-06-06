import itertools
import logging
import os
from typing import List, Optional, Type

from pydantic import AnyUrl, ValidationError

import cumulusci.core.dependencies.base as base_dependency
from cumulusci.core.config import OrgConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.exceptions import DependencyParseError
from cumulusci.salesforce_api.package_install import (
    DEFAULT_PACKAGE_RETRY_OPTIONS,
    PackageInstallOptions,
    install_package_by_namespace_version,
    install_package_by_version_id,
)
from cumulusci.utils import download_extract_zip

logger = logging.getLogger(__name__)


class PackageNamespaceVersionDependency(base_dependency.StaticDependency):
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


class PackageVersionIdDependency(base_dependency.StaticDependency):
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


class UnmanagedZipURLDependency(base_dependency.UnmanagedDependency):
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


#### Definition of dependency classes ####

AVAILABLE_DEPENDENCY_CLASSES = [
    PackageVersionIdDependency,
    PackageNamespaceVersionDependency,
    UnmanagedZipURLDependency,
]


def add_dependency_class(new_class: Type[base_dependency.Dependency]) -> None:
    """
    Adds a new dependency class to the global list if it's not already present.
    Args:
        new_class: The dependency class to add.
    """
    if new_class not in AVAILABLE_DEPENDENCY_CLASSES:
        AVAILABLE_DEPENDENCY_CLASSES.append(new_class)
        logger.debug(f"dependency_config: Added '{new_class}'.")
    else:
        logger.debug(f"dependency_config: '{new_class}' already exists.")


def parse_dependency(dep_dict: dict[str, str]) -> Optional[base_dependency.Dependency]:
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
        except ValidationError:
            pass


def parse_dependencies(
    deps: Optional[List[dict[str, str]]]
) -> List[base_dependency.Dependency]:
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


#### Definition of dependency pins classes ####

AVAILABLE_DEPENDENCY_PIN_CLASSES = []


def parse_pins(pins: Optional[List[dict]]) -> List[base_dependency.DependencyPin]:
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


def add_dependency_pin_class(new_class: Type[base_dependency.DependencyPin]) -> None:
    """
    Adds a new dependency pin class to the global list if it's not already present.
    Args:
        new_class: The dependency pin class to add.
    """
    if new_class not in AVAILABLE_DEPENDENCY_PIN_CLASSES:
        AVAILABLE_DEPENDENCY_PIN_CLASSES.append(new_class)
        logger.info(f"dependency_pin_config: Added '{new_class}'.")
    else:
        logger.warning(f"dependency_pin_config: '{new_class}' already exists.")


def parse_dependency_pin(
    pin_dict: dict[str, str]
) -> Optional[base_dependency.DependencyPin]:
    """Parse a single dependency pin specification in the form of a dict
    into a concrete DependencyPin subclass.

    Returns None if the given dict cannot be parsed."""

    for dependency_pin_class in AVAILABLE_DEPENDENCY_PIN_CLASSES:
        try:
            pin = dependency_pin_class.parse_obj(pin_dict)
            if pin:
                return pin
        except ValidationError:
            pass
