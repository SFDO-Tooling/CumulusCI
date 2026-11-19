"""Resolve Salesforce DX project dependencies through the Dev Hub Tooling API."""

import json
import re
from functools import cached_property

from requests.exceptions import RequestException
from simple_salesforce import format_soql
from simple_salesforce.exceptions import SalesforceError

from cumulusci.core.config.util import get_devhub_config
from cumulusci.core.dependencies.dependencies import PackageVersionIdDependency
from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection

PACKAGE_ID = re.compile(r"0Ho[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?")
VERSION_ID = re.compile(r"04t[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?")
VERSION_NUMBER = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+|LATEST|RELEASED)")


class SfdxPackageVersionDependency(PackageVersionIdDependency):
    """An installable package version with optional Dev Hub package identity."""

    package2_id: str | None = None
    source: str


def load_sfdx_project(contents, source):
    """Read JSON and validate the project structure used during import and resolution."""
    try:
        project = json.loads(contents)
    except ValueError as exc:
        raise DependencyResolutionError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(project, dict):
        raise DependencyResolutionError(f"Expected a JSON object in {source}.")

    directories = project.get("packageDirectories")
    if not isinstance(directories, list) or any(
        not isinstance(directory, dict) for directory in directories
    ):
        raise DependencyResolutionError(
            f"Expected a packageDirectories array in {source}."
        )
    if not isinstance(project.get("packageAliases", {}), dict):
        raise DependencyResolutionError(
            f"Expected a packageAliases object in {source}."
        )
    for directory in directories:
        if not isinstance(directory.get("path"), str):
            raise DependencyResolutionError(
                f"Expected a package directory path in {source}."
            )
        if not isinstance(directory.get("dependencies", []), list):
            raise DependencyResolutionError(
                f"Expected a dependencies array for {directory['path']!r} in {source}."
            )
    return project


def resolve_project_dependencies(context, contents, source, package_directory):
    """Resolve each package directory's declarations in file order."""
    project = load_sfdx_project(contents, source)
    directories = project["packageDirectories"]
    if package_directory is not None:
        directories = [
            directory
            for directory in directories
            if directory["path"] == package_directory
        ]
        if len(directories) != 1:
            raise DependencyResolutionError(
                f"Expected one package directory with path {package_directory!r} in {source}."
            )

    resolver = ProjectPackageResolver(context, project.get("packageAliases", {}))
    resolved = []
    for directory in directories:
        declarations = directory.get("dependencies", [])
        location = f"{source}, package directory {directory.get('path')!r}"
        for index, declaration in enumerate(declarations, start=1):
            try:
                resolved.append(
                    resolver.resolve(declaration, directory.get("branch"), location)
                )
            except (
                DependencyResolutionError,
                SalesforceError,
                RequestException,
            ) as exc:
                raise DependencyResolutionError(
                    f"Cannot resolve dependency {index} {declaration!r} in {location}: {exc}"
                ) from exc
    return resolved


class ProjectPackageResolver:
    """Resolve aliases and version selectors for one project file."""

    def __init__(self, context, aliases):
        self.context = context
        self.aliases = aliases

    @cached_property
    def tooling(self):
        try:
            if self.context.keychain is None:
                raise DependencyResolutionError(
                    "No CumulusCI project keychain is available."
                )
            hub = get_devhub_config(self.context)
            return get_simple_salesforce_connection(
                self.context, hub, base_url="tooling"
            )
        except Exception as exc:
            raise DependencyResolutionError(
                f"Cannot connect to the configured Dev Hub. Check Salesforce CLI authentication and CumulusCI's devhub service. {exc}"
            ) from exc

    def resolve(self, declaration, inherited_branch, source):
        """Resolve one Salesforce dependency declaration to an installable ID."""
        if not isinstance(declaration, dict):
            raise DependencyResolutionError("Expected a dependency object.")
        explicit_version = declaration.get("subscriberPackageVersionId")
        if explicit_version is not None:
            return self._dependency(explicit_version, source)

        identifiers = [
            declaration[key] for key in ("package", "packageId") if key in declaration
        ]
        if len(identifiers) != 1 or not isinstance(identifiers[0], str):
            raise DependencyResolutionError("Specify one package alias or package ID.")
        identifier = identifiers[0]
        package_id = self.aliases.get(identifier, identifier)
        if isinstance(package_id, str) and VERSION_ID.fullmatch(package_id):
            return self._dependency(package_id, source)
        if not isinstance(package_id, str) or not PACKAGE_ID.fullmatch(package_id):
            raise DependencyResolutionError(
                f"{identifier!r} must be a 0Ho or 04t ID, or an alias for one in packageAliases."
            )

        version = declaration.get("versionNumber")
        match = VERSION_NUMBER.fullmatch(version) if isinstance(version, str) else None
        if not match:
            raise DependencyResolutionError(
                f"Package {identifier!r} needs versionNumber in MAJOR.MINOR.PATCH.BUILD format. "
                "BUILD can be a number, LATEST, or RELEASED."
            )
        branch = declaration.get("branch")
        if branch is None:
            branch = inherited_branch
        if branch is not None and not isinstance(branch, str):
            raise DependencyResolutionError("branch must be a string.")

        major, minor, patch, build = match.groups()
        where = format_soql(
            "Package2Id = {} AND MajorVersion = {} AND MinorVersion = {} AND PatchVersion = {}",
            package_id,
            int(major),
            int(minor),
            int(patch),
        )
        scope = self._version_scope(build, branch)
        if build in ("LATEST", "RELEASED"):
            build_number = self._max_build(where, scope)
            # Salesforce falls back to the null branch only for inherited LATEST.
            if (
                build_number is None
                and build == "LATEST"
                and branch
                and "branch" not in declaration
            ):
                scope = self._version_scope(build, None)
                build_number = self._max_build(where, scope)
            if build_number is None:
                raise DependencyResolutionError(
                    f"No eligible {version} version of {identifier!r} ({package_id}) in the configured Dev Hub ({scope})."
                )
        else:
            build_number = int(build)

        records = self.tooling.query(
            f"SELECT SubscriberPackageVersionId FROM Package2Version WHERE {where} "
            f"AND BuildNumber = {int(build_number)} AND {scope} LIMIT 2"
        )["records"]
        if len(records) != 1:
            problem = (
                "No matching version" if not records else "Multiple matching versions"
            )
            raise DependencyResolutionError(
                f"{problem} for {identifier!r} ({package_id}) at {version} in the configured Dev Hub ({scope})."
            )
        return self._dependency(
            records[0].get("SubscriberPackageVersionId"), source, package_id
        )

    @staticmethod
    def _version_scope(build, branch):
        if build == "RELEASED":
            return "IsReleased = true"
        return format_soql("Branch = {}", branch or None)

    def _max_build(self, where, scope):
        records = self.tooling.query(
            f"SELECT MAX(BuildNumber) FROM Package2Version WHERE {where} "
            f"AND {scope} AND IsDeprecated != true"
        )["records"]
        return records[0].get("expr0") if records else None

    @staticmethod
    def _dependency(version_id, source, package_id=None):
        if not isinstance(version_id, str) or not VERSION_ID.fullmatch(version_id):
            raise DependencyResolutionError(
                f"Expected a valid 04t package version ID, got {version_id!r}."
            )
        return SfdxPackageVersionDependency(
            version_id=version_id, package2_id=package_id, source=source
        )
