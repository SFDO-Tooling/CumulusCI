from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig
from typing import Optional, Union
import base64
import enum
import io
import json
import pathlib
import re
import zipfile

from pydantic import BaseModel, validator
from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.dependencies.dependencies import (
    ManagedPackageDependency,
    UnmanagedDependency,
    get_resolver_stack,
    get_static_dependencies,
    parse_dependencies,
)
from cumulusci.core.exceptions import DependencyLookupError, ServiceNotConfigured
from cumulusci.core.exceptions import GithubException
from cumulusci.core.exceptions import PackageUploadFailure
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.package_zip import BasePackageZipBuilder
from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.core.sfdx import get_default_devhub_username
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.tasks.salesforce.org_settings import build_settings_package
from cumulusci.utils import download_extract_github

VERSION_RE = re.compile(
    r"^(?P<MajorVersion>\d+)"
    r".(?P<MinorVersion>\d+)"
    r"(\.(?P<PatchVersion>\d+))?"
    r"(\.(?P<BuildNumber>\d+))?"
    r"( \(Beta (?P<BetaNumber>\d+)\))?$"
)


class PackageTypeEnum(str, enum.Enum):
    managed = "Managed"
    unlocked = "Unlocked"


class VersionTypeEnum(str, enum.Enum):
    major = "major"
    minor = "minor"
    patch = "patch"
    build = "build"


class PackageVersionNumber(BaseModel):
    """A Salesforce package version parsed into components."""

    MajorVersion: int = 0
    MinorVersion: int = 0
    PatchVersion: int = 0
    BuildNumber: Union[int, str] = 0
    IsReleased: bool = False

    def format(self):
        """Format version number as a string"""
        return f"{self.MajorVersion}.{self.MinorVersion}.{self.PatchVersion}.{self.BuildNumber}"

    @classmethod
    def parse(cls, s: str):
        """Parse a version number from a string"""
        match = VERSION_RE.match(s)
        if not match:
            raise ValueError(f"Could not parse version number: {s}")
        return PackageVersionNumber(
            MajorVersion=int(match.group("MajorVersion")),
            MinorVersion=int(match.group("MinorVersion")),
            PatchVersion=int(match.group("PatchVersion") or 0),
            BuildNumber=int(
                match.group("BuildNumber") or match.group("BetaNumber") or 0
            ),
            IsReleased=not bool(match.group("BetaNumber")),
        )

    def increment(self, version_type: VersionTypeEnum = VersionTypeEnum.build):
        """Construct a new PackageVersionNumber by incrementing the specified component."""
        parts = {
            "MajorVersion": self.MajorVersion,
            "MinorVersion": self.MinorVersion,
            "PatchVersion": self.PatchVersion,
            "BuildNumber": "NEXT",
            "IsReleased": False,
        }
        if self.IsReleased:
            if version_type == VersionTypeEnum.major:
                parts["MajorVersion"] += 1
                parts["MinorVersion"] = 0
                parts["PatchVersion"] = 0
            if version_type == VersionTypeEnum.minor:
                parts["MinorVersion"] += 1
                parts["PatchVersion"] = 0
            elif version_type == VersionTypeEnum.patch:
                parts["PatchVersion"] += 1
        return PackageVersionNumber(**parts)


class PackageConfig(BaseModel):
    package_name: str
    description: str = ""
    package_type: PackageTypeEnum
    org_dependent: bool = False
    post_install_script: Optional[str]
    uninstall_script: Optional[str]
    namespace: Optional[str]
    version_name: str
    version_base: Optional[str]
    version_type: VersionTypeEnum = VersionTypeEnum.minor

    @validator("org_dependent")
    def org_dependent_must_be_unlocked(cls, v, values):
        if v and values["package_type"] != PackageTypeEnum.unlocked:
            raise ValueError("Only unlocked packages can be org-dependent.")
        return v

    @validator("post_install_script")
    def post_install_script_must_be_managed(cls, v, values):
        if v and values["package_type"] != PackageTypeEnum.managed:
            raise ValueError("Only managed packages can have a post-install script.")
        return v

    @validator("uninstall_script")
    def uninstall_script_must_be_managed(cls, v, values):
        if v and values["package_type"] != PackageTypeEnum.managed:
            raise ValueError("Only managed packages can have an uninstall script.")
        return v


class CreatePackageVersion(BaseSalesforceApiTask):
    """Creates a new second-generation package version.

    If a package named ``package_name`` does not yet exist in the Dev Hub, it will be created.
    """

    api_version = "50.0"

    task_options = {
        "package_name": {"description": "Name of package"},
        "package_type": {
            "description": "Package type (Unlocked or Managed)",
            "required": True,
        },
        "namespace": {"description": "Package namespace"},
        "version_name": {"description": "Version name"},
        "version_base": {
            "description": "The version number to use as a base before incrementing. "
            "Optional; defaults to the highest existing version number of this package. "
            "Can be set to ``latest_github_release`` to use the version of the most recent release published to GitHub."
        },
        "version_type": {
            "description": "The part of the version number to increment. "
            "Options are major, minor, patch, build.  Defaults to build"
        },
        "skip_validation": {
            "description": "If true, skip validation of the package version. Default: false. "
            "Skipping validation creates packages more quickly, but they cannot be promoted for release."
        },
        "org_dependent": {
            "description": "If true, create an org-dependent unlocked package. Default: false."
        },
        "post_install_script": {
            "description": "Post-install script (for managed packages)",
        },
        "uninstall_script": {
            "description": "Uninstall script (for managed packages)",
        },
        "force_upload": {
            "description": "If true, force creating a new package version even if one with the same contents already exists"
        },
        "static_resource_path": {
            "description": "The path where decompressed static resources are stored. Any subdirectories found will be zipped and added to the staticresources directory of the build."
        },
        "resolution_strategy": {
            "description": "The name of a sequence of resolution_strategy (from project__dependency_resolutions) to apply to dynamic dependencies. Defaults to 'production'."
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.package_config = PackageConfig(
            package_name=self.options.get("package_name")
            or self.project_config.project__package__name,
            package_type=self.options.get("package_type")
            or self.project_config.project__package__type,
            org_dependent=self.options.get("org_dependent", False),
            post_install_script=self.options.get("post_install_script")
            or self.project_config.project__package__install_class,
            uninstall_script=self.options.get("uninstall_script")
            or self.project_config.project__package__uninstall_class,
            namespace=self.options.get("namespace")
            or self.project_config.project__package__namespace,
            version_name=self.options.get("version_name") or "Release",
            version_base=self.options.get("version_base"),
            version_type=self.options.get("version_type") or "minor",
        )
        self.options["skip_validation"] = process_bool_arg(
            self.options.get("skip_validation") or False
        )
        self.options["force_upload"] = process_bool_arg(
            self.options.get("force_upload") or False
        )

    def _init_task(self):
        self.devhub_config = self._init_devhub()
        self.tooling = get_simple_salesforce_connection(
            self.project_config,
            self.devhub_config,
            api_version=self.api_version,
            base_url="tooling",
        )

    def _init_devhub(self):
        # Determine the devhub username for this project
        try:
            devhub_service = self.project_config.keychain.get_service("devhub")
        except ServiceNotConfigured:
            devhub_username = get_default_devhub_username()
        else:
            devhub_username = devhub_service.username
        return SfdxOrgConfig({"username": devhub_username}, "devhub")

    def _run_task(self):
        """Creates a new 2GP package version.

        1. Create package if not found in Dev Hub.
        2. Request creation of package version.
        3. Wait for completion.
        4. Collect package information as return values.
        """
        # find existing package in Dev Hub, or create one if necessary
        self.package_id = self._get_or_create_package(self.package_config)
        self.return_values["package_id"] = self.package_id

        # submit request to create package version
        options = {
            "package_type": self.package_config.package_type.value,
            "namespace_inject": self.package_config.namespace,
            "namespaced_org": self.package_config.namespace is not None,
        }
        if "static_resource_path" in self.options:
            options["static_resource_path"] = self.options["static_resource_path"]

        package_zip_builder = MetadataPackageZipBuilder(
            path=self.project_config.default_package_path,
            name=self.package_config.package_name,
            options=options,
            logger=self.logger,
        )
        self.request_id = self._create_version_request(
            self.package_id,
            self.package_config,
            package_zip_builder,
            self.options["skip_validation"],
        )
        self.return_values["request_id"] = self.request_id

        # wait for request to complete
        self._poll()
        self.return_values["package2_version_id"] = self.package_version_id

        # get the new version number from Package2Version
        res = self.tooling.query(
            "SELECT MajorVersion, MinorVersion, PatchVersion, BuildNumber, SubscriberPackageVersionId FROM Package2Version WHERE Id='{}' ".format(
                self.package_version_id
            )
        )
        package2_version = res["records"][0]
        self.return_values["subscriber_package_version_id"] = package2_version[
            "SubscriberPackageVersionId"
        ]
        self.return_values["version_number"] = PackageVersionNumber(
            **package2_version
        ).format()

        # get the new version's dependencies from SubscriberPackageVersion
        res = self.tooling.query(
            "SELECT Dependencies FROM SubscriberPackageVersion "
            f"WHERE Id='{package2_version['SubscriberPackageVersionId']}'"
        )
        self.return_values["dependencies"] = res["records"][0]["Dependencies"]

        self.logger.info("Created package version:")
        self.logger.info(f"  Package2 Id: {self.package_id}")
        self.logger.info(f"  Package2Version Id: {self.package_version_id}")
        self.logger.info(
            f"  SubscriberPackageVersion Id: {self.return_values['subscriber_package_version_id']}"
        )
        self.logger.info(f"  Version Number: {self.return_values['version_number']}")
        self.logger.info(f"  Dependencies: {self.return_values['dependencies']}")

    def _get_or_create_package(self, package_config: PackageConfig):
        """Find or create the Package2

        Checks the Dev Hub for an existing, non-deprecated 2GP package
        with matching name, type, and namespace.
        """
        message = f"Checking for existing {package_config.package_type} Package named {package_config.package_name}"
        query = (
            f"SELECT Id, ContainerOptions FROM Package2 WHERE IsDeprecated = FALSE "
            f"AND ContainerOptions='{package_config.package_type}' "
            f"AND IsOrgDependent={package_config.org_dependent} "
            f"AND Name='{package_config.package_name}'"
        )
        if package_config.namespace:
            query += f" AND NamespacePrefix='{package_config.namespace}'"
            message += f" with namespace {package_config.namespace}"
        else:
            query += " AND NamespacePrefix=null"
        self.logger.info(message)
        try:
            res = self.tooling.query(query)
        except SalesforceMalformedRequest as err:
            if "Object type 'Package2' is not supported" in err.content[0]["message"]:
                raise TaskOptionsError(
                    "This org does not have a Dev Hub with 2nd-generation packaging enabled. "
                    "Make sure you are using the correct org and/or check the Dev Hub settings in Setup."
                )
            raise  # pragma: no cover
        if res["size"] > 1:
            raise TaskOptionsError(
                f"Found {res['size']} packages with the same name, namespace, and package_type"
            )
        if res["size"] == 1:
            existing_package = res["records"][0]
            if existing_package["ContainerOptions"] != package_config.package_type:
                raise PackageUploadFailure(
                    f"Duplicate Package: {existing_package['ContainerOptions']} package with id "
                    f"{ existing_package['Id']} has the same name ({package_config.package_name}) "
                    "for this namespace but has a different package type"
                )
            package_id = existing_package["Id"]
            self.logger.info(f"Found {package_id}")
            return package_id

        self.logger.info("No existing package found, creating the package")
        Package2 = self._get_tooling_object("Package2")
        package = Package2.create(
            {
                "ContainerOptions": package_config.package_type,
                "IsOrgDependent": package_config.org_dependent,
                "Name": package_config.package_name,
                "Description": package_config.description,
                "NamespacePrefix": package_config.namespace,
            }
        )
        return package["id"]

    def _create_version_request(
        self,
        package_id: str,
        package_config: PackageConfig,
        package_zip_builder: BasePackageZipBuilder,
        skip_validation: bool = False,
        dependencies: list = None,
    ):
        # Prepare the VersionInfo file
        version_bytes = io.BytesIO()
        version_info = zipfile.ZipFile(version_bytes, "w", zipfile.ZIP_DEFLATED)
        try:

            # Add the package.zip
            package_hash = package_zip_builder.as_hash()
            version_info.writestr("package.zip", package_zip_builder.as_bytes())

            if not self.options["force_upload"]:
                # Check for an existing package with the same contents
                res = self.tooling.query(
                    "SELECT Id "
                    "FROM Package2VersionCreateRequest "
                    f"WHERE Package2Id = '{package_id}' "
                    "AND Status != 'Error' "
                    f"AND SkipValidation = {str(skip_validation)} "
                    f"AND Tag = 'hash:{package_hash}' "
                    "ORDER BY CreatedDate DESC"
                )
                if res["size"] > 0:
                    self.logger.info(
                        "Found existing request for package with the same metadata.  Using existing package."
                    )
                    return res["records"][0]["Id"]

            # Create the package descriptor
            version_number = self._get_base_version_number(
                package_config.version_base, package_id
            ).increment(package_config.version_type)
            package_descriptor = {
                "ancestorId": "",  # @@@ need to add this for Managed 2gp
                "id": package_id,
                "path": "",
                "versionName": package_config.version_name,
                "versionNumber": version_number.format(),
            }
            if package_config.post_install_script:
                package_descriptor[
                    "postInstallScript"
                ] = package_config.post_install_script
            if package_config.uninstall_script:
                package_descriptor["uninstallScript"] = package_config.uninstall_script

            # Add org shape
            with open(self.org_config.config_file, "r") as f:
                scratch_org_def = json.load(f)
            for key in (
                "country",
                "edition",
                "language",
                "features",
                "snapshot",
            ):
                if key in scratch_org_def:
                    package_descriptor[key] = scratch_org_def[key]

            # Add settings
            if "settings" in scratch_org_def:
                with build_settings_package(
                    scratch_org_def["settings"], self.api_version
                ) as path:
                    settings_zip_builder = MetadataPackageZipBuilder(path=path)
                    version_info.writestr(
                        "settings.zip", settings_zip_builder.as_bytes()
                    )

            # Add the dependencies for the package
            is_dependency = package_config is not self.package_config
            if (
                not (package_config.org_dependent or skip_validation)
                and not is_dependency
            ):
                self.logger.info("Determining dependencies for package")
                dependencies = self._get_dependencies()
            if dependencies:
                package_descriptor["dependencies"] = dependencies

            # Add package descriptor to version info
            version_info.writestr(
                "package2-descriptor.json", json.dumps(package_descriptor)
            )
        finally:
            version_info.close()
        version_info = base64.b64encode(version_bytes.getvalue()).decode("utf-8")
        Package2CreateVersionRequest = self._get_tooling_object(
            "Package2VersionCreateRequest"
        )
        request = {
            "Package2Id": package_id,
            "SkipValidation": skip_validation,
            "Tag": f"hash:{package_hash}",
            "VersionInfo": version_info,
        }
        self.logger.info(
            f"Requesting creation of package version {version_number.format()} "
            f"for package {package_config.package_name} ({package_id})"
        )
        response = Package2CreateVersionRequest.create(request)
        self.logger.info(
            f"Package2VersionCreateRequest created with id {response['id']}"
        )
        return response["id"]

    def _get_base_version_number(
        self, version_base: Optional[str], package_id: str
    ) -> PackageVersionNumber:
        """Determine the "base version" of the package (existing version to be incremented)"""
        if version_base is None:
            # Default: Get the highest existing version of the package
            res = self.tooling.query(
                "SELECT MajorVersion, MinorVersion, PatchVersion, BuildNumber, IsReleased "
                "FROM Package2Version "
                f"WHERE Package2Id='{package_id}' "
                "ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion DESC, BuildNumber DESC "
                "LIMIT 1"
            )
            if res["size"]:
                return PackageVersionNumber(**res["records"][0])
        elif version_base == "latest_github_release":
            # Get the version of the latest github release
            try:
                return PackageVersionNumber.parse(
                    str(self.project_config.get_latest_version())
                )
            except GithubException:
                # handle case where there isn't a release yet
                pass
        else:
            return PackageVersionNumber.parse(version_base)
        return PackageVersionNumber()

    def _get_dependencies(self):
        """Resolve dependencies into SubscriberPackageVersionIds (04t prefix)"""
        dependencies = get_static_dependencies(
            parse_dependencies(self.project_config.project__dependencies),
            get_resolver_stack(
                self.project_config,
                self.options.get("resolution_strategy") or "production",
            ),
            self.project_config,
        )

        # If any dependencies are expressed as a 1gp namespace + version,
        # we need to convert those to 04t package version ids,
        # for which we need an org with the packages installed.
        if self._has_1gp_namespace_dependency(dependencies):
            dependencies = self.org_config.resolve_04t_dependencies(dependencies)

        # Convert dependencies to correct format for Package2VersionCreateRequest
        dependencies = self._convert_project_dependencies(dependencies)

        # Build additional packages for local unpackaged/pre
        dependencies = self._get_unpackaged_pre_dependencies(dependencies)

        return dependencies

    def _has_1gp_namespace_dependency(self, project_dependencies):
        """Returns true if any dependencies are specified using a namespace rather than 04t"""
        for dependency in project_dependencies:
            if (
                isinstance(dependency, ManagedPackageDependency)
                and dependency.namespace
            ):
                return True

        return False

    def _convert_project_dependencies(self, dependencies):
        """Convert dependencies into the format expected by Package2VersionCreateRequest.

        For dependencies expressed as a GitHub repo subfolder, build an unlocked package from that.
        """
        new_dependencies = []
        for dependency in dependencies:
            new_dependency = {}
            if (
                isinstance(dependency, ManagedPackageDependency)
                and dependency.version_id
            ):
                self.logger.info(
                    f"Adding dependency {dependency.package_name} with id {dependency.version_id}"
                )
                new_dependency["subscriberPackageVersionId"] = dependency.version_id

            elif isinstance(dependency, UnmanagedDependency) and dependency.repo_name:
                # TODO: We do not support zip_url unmanaged dependencies
                version_id = self._create_unlocked_package_from_github(
                    dependency, new_dependencies
                )
                self.logger.info(f"Adding dependency {dependency} with id {version_id}")
                new_dependency["subscriberPackageVersionId"] = version_id

            else:
                raise DependencyLookupError(
                    f"Unable to convert dependency: {dependency}"
                )

            new_dependencies.append(new_dependency)

        return new_dependencies

    def _get_unpackaged_pre_dependencies(self, dependencies):
        """Create package for unpackaged/pre metadata, if necessary"""
        path = pathlib.Path("unpackaged", "pre")
        if not path.exists():
            return dependencies

        for item_path in sorted(path.iterdir(), key=str):
            if item_path.is_dir():
                version_id = self._create_unlocked_package_from_local(
                    item_path, dependencies
                )
                self.logger.info(
                    "Adding dependency {}/{} {} with id {}".format(
                        self.project_config.repo_owner,
                        self.project_config.repo_name,
                        item_path,
                        version_id,
                    )
                )
                dependencies.append({"subscriberPackageVersionId": version_id})

        return dependencies

    def _create_unlocked_package_from_github(self, dependency, dependencies):
        gh_for_repo = self.project_config.get_github_api(
            dependency.repo_owner, dependency.repo_name
        )
        zip_src = download_extract_github(
            gh_for_repo,
            dependency.repo_owner,
            dependency.repo_name,
            dependency.subfolder,
            ref=dependency.ref,
        )
        keys = ["namespace_inject", "namespace_strip", "unmanaged"]
        dep_opts = dependency.dict(exclude_none=True)
        options = {k: dep_opts[k] for k in keys if k in dep_opts}
        package_zip_builder = MetadataPackageZipBuilder.from_zipfile(
            zip_src, options=options, logger=self.logger
        )

        package_config = PackageConfig(
            package_name=f"{dependency.repo_owner}/{dependency.repo_name} {dependency.subfolder}",
            version_name="Auto",
            package_type="Unlocked",
            # Ideally we'd do this without a namespace,
            # but it needs to match the dependent package
            namespace=self.package_config.namespace,
        )
        package_id = self._get_or_create_package(package_config)
        self.request_id = self._create_version_request(
            package_id,
            package_config,
            package_zip_builder,
            dependencies=dependencies,
        )

        self._poll()
        self._reset_poll()
        res = self.tooling.query(
            "SELECT SubscriberPackageVersionId FROM Package2Version "
            f"WHERE Id='{self.package_version_id}'"
        )
        package2_version = res["records"][0]
        return package2_version["SubscriberPackageVersionId"]

    def _create_unlocked_package_from_local(self, path, dependencies):
        """Create an unlocked package version from a local directory."""
        self.logger.info("Creating package for dependencies in {}".format(path))
        package_name = (
            f"{self.project_config.repo_owner}/{self.project_config.repo_name} {path}"
        )
        package_zip_builder = MetadataPackageZipBuilder(
            path=path, name=package_name, logger=self.logger
        )
        package_config = PackageConfig(
            package_name=package_name,
            version_name="Auto",
            package_type="Unlocked",
            # Ideally we'd do this without a namespace,
            # but it needs to match the dependent package
            namespace=self.package_config.namespace,
        )
        package_id = self._get_or_create_package(package_config)
        self.request_id = self._create_version_request(
            package_id, package_config, package_zip_builder, dependencies=dependencies
        )
        self._poll()
        self._reset_poll()
        res = self.tooling.query(
            "SELECT SubscriberPackageVersionId FROM Package2Version "
            f"WHERE Id='{self.package_version_id}'"
        )
        package2_version = res["records"][0]
        return package2_version["SubscriberPackageVersionId"]

    def _poll_action(self):
        """Check if Package2VersionCreateRequest has completed."""
        res = self.tooling.query(
            f"SELECT Id, Status, Package2VersionId FROM Package2VersionCreateRequest WHERE Id = '{self.request_id}'"
        )
        request = res["records"][0]
        if request["Status"] == "Success":
            self.logger.info("[Success]: Package creation successful")
            self.poll_complete = True
            self.package_version_id = request["Package2VersionId"]
        elif request["Status"] == "Error":
            self.logger.error("[Error]: Package creation failed with error:")
            res = self.tooling.query(
                "SELECT Message FROM Package2VersionCreateRequestError "
                f"WHERE ParentRequestId = '{request['Id']}'"
            )
            errors = []
            if res["size"] > 0:
                for error in res["records"]:
                    errors.append(error["Message"])
                    self.logger.error(error["Message"])
            raise PackageUploadFailure("\n".join(errors))
        else:
            self.logger.info(f"[{request['Status']}]")
