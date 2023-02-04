import base64
import enum
import io
import json
import pathlib
import zipfile
from typing import List, Optional

from pydantic import BaseModel, validator
from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.config.util import get_devhub_config
from cumulusci.core.dependencies.dependencies import (
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
    UnmanagedDependency,
    UnmanagedGitHubRefDependency,
)
from cumulusci.core.dependencies.resolvers import get_static_dependencies
from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.core.exceptions import (
    CumulusCIUsageError,
    DependencyLookupError,
    GithubException,
    PackageUploadFailure,
    TaskOptionsError,
)
from cumulusci.core.github import get_version_id_from_tag
from cumulusci.core.sfdx import convert_sfdx_source
from cumulusci.core.utils import process_bool_arg
from cumulusci.core.versions import PackageType, PackageVersionNumber, VersionTypeEnum
from cumulusci.salesforce_api.package_zip import (
    BasePackageZipBuilder,
    MetadataPackageZipBuilder,
)
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask
from cumulusci.tasks.salesforce.org_settings import build_settings_package
from cumulusci.utils.git import split_repo_url


class PackageTypeEnum(str, enum.Enum):
    managed = "Managed"
    unlocked = "Unlocked"


class PackageConfig(BaseModel):
    package_name: str
    description: str = ""
    package_type: PackageTypeEnum
    org_dependent: bool = False
    post_install_script: Optional[str] = None
    uninstall_script: Optional[str] = None
    namespace: Optional[str] = None
    version_name: str
    version_base: Optional[str] = None
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

    api_version = "52.0"

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
        "install_key": {
            "description": "Install key for package. Default is no install key."
        },
        "force_upload": {
            "description": "If true, force creating a new package version even if one with the same contents already exists"
        },
        "static_resource_path": {
            "description": "The path where decompressed static resources are stored. "
            "Any subdirectories found will be zipped and added to the staticresources directory of the build."
        },
        "ancestor_id": {
            "description": "The 04t Id to use for the ancestor of this package. "
            "Optional; defaults to no ancestor specified. "
            "Can be set to ``latest_github_release`` to use the most recent production version published to GitHub."
        },
        "resolution_strategy": {
            "description": "The name of a sequence of resolution_strategy "
            "(from project__dependency_resolutions) to apply to dynamic dependencies. Defaults to 'production'."
        },
        "create_unlocked_dependency_packages": {
            "description": "If True, create unlocked packages for unpackaged metadata in this project and dependencies. "
            "Defaults to False."
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        # Allow these fields to be explicitly set to blanks
        # so that unlocked builds can override an otherwise-configured
        # postinstall script
        if "post_install_script" in self.options:
            post_install_script = self.options["post_install_script"]
        else:
            post_install_script = self.project_config.project__package__install_class

        if "uninstall_script" in self.options:
            uninstall_script = self.options["uninstall_script"]
        else:
            uninstall_script = self.project_config.project__package__uninstall_class

        self.package_config = PackageConfig(
            package_name=self.options.get("package_name")
            or self.project_config.project__package__name,
            package_type=self.options.get("package_type")
            or self.project_config.project__package__type,
            org_dependent=self.options.get("org_dependent", False),
            post_install_script=post_install_script,
            uninstall_script=uninstall_script,
            namespace=self.options.get("namespace")
            or self.project_config.project__package__namespace,
            version_name=self.options.get("version_name") or "Release",
            version_base=self.options.get("version_base"),
            version_type=self.options.get("version_type") or VersionTypeEnum("build"),
        )
        self.options["skip_validation"] = process_bool_arg(
            self.options.get("skip_validation") or False
        )
        self.options["force_upload"] = process_bool_arg(
            self.options.get("force_upload") or False
        )
        self.options["create_unlocked_dependency_packages"] = process_bool_arg(
            self.options.get("create_unlocked_dependency_packages") or False
        )

    def _init_task(self):
        self.tooling = get_simple_salesforce_connection(
            self.project_config,
            get_devhub_config(self.project_config),
            api_version=self.api_version,
            base_url="tooling",
        )
        self.context = TaskContext(self.org_config, self.project_config, self.logger)

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

        package_zip_builder = None
        with convert_sfdx_source(
            self.project_config.default_package_path,
            self.package_config.package_name,
            self.logger,
        ) as path:
            package_zip_builder = MetadataPackageZipBuilder(
                path=path,
                name=self.package_config.package_name,
                options=options,
                context=self.context,
            )

        ancestor_id = self._resolve_ancestor_id(self.options.get("ancestor_id"))

        self.request_id = self._create_version_request(
            self.package_id,
            self.package_config,
            package_zip_builder,
            ancestor_id,
            self.options["skip_validation"],
        )
        self.return_values["request_id"] = self.request_id

        # wait for request to complete
        self._poll()
        self.return_values["package2_version_id"] = self.package_version_id

        # get the new version number from Package2Version
        res = self.tooling.query(
            f"SELECT MajorVersion, MinorVersion, PatchVersion, BuildNumber, SubscriberPackageVersionId FROM Package2Version WHERE Id='{self.package_version_id}'"
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
        self.return_values["dependencies"] = self._prepare_cci_dependencies(
            res["records"][0]["Dependencies"]
        )

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
        ancestor_id: str = "",
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
                "id": package_id,
                "path": "",
                "versionName": package_config.version_name,
                "versionNumber": version_number.format(),
                "ancestorId": ancestor_id,
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

            # See https://github.com/forcedotcom/packaging/blob/main/src/package/packageVersionCreate.ts#L358
            # Note that we handle orgPreferences below by converting to settings,
            # in build_settings_package()
            for key in (
                "country",
                "edition",
                "language",
                "features",
                "snapshot",
                "release",
                "sourceOrg",
            ):
                if key in scratch_org_def:
                    package_descriptor[key] = scratch_org_def[key]

            # Add settings
            if "settings" in scratch_org_def or "objectSettings" in scratch_org_def:
                with build_settings_package(
                    scratch_org_def.get("settings"),
                    scratch_org_def.get("objectSettings"),
                    self.api_version,
                ) as path:
                    settings_zip_builder = MetadataPackageZipBuilder(
                        path=path, context=self.context
                    )
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
            "CalculateCodeCoverage": not skip_validation,
        }
        if "install_key" in self.options:
            request["InstallKey"] = self.options["install_key"]

        self.logger.info(
            f"Requesting creation of package version {version_number.format()} "
            f"for package {package_config.package_name} ({package_id})"
        )
        response = Package2CreateVersionRequest.create(request)
        self.logger.info(
            f"Package2VersionCreateRequest created with id {response['id']}"
        )
        return response["id"]

    def _resolve_ancestor_id(self, spv_id: Optional[str] = None) -> str:
        """
        If an ancestor_id (04t) is not specified, get it
        from the latest production release.

        @param spv_id The SubscriberPackageVersionId (04t) that is the ancestor
        to the version being created.
        """
        if not spv_id:
            return ""
        elif self.package_config.package_type == PackageTypeEnum.unlocked:
            raise CumulusCIUsageError(
                "Cannot specify an ancestor for Unlocked packages."
            )
        elif spv_id.startswith("04t"):
            return self._convert_ancestor_id(spv_id)
        elif spv_id == "latest_github_release":
            try:
                tag_name = self.project_config.get_latest_tag(beta=False)
            except GithubException:
                # No release found
                return ""
            repo = self.project_config.get_repo()
            spv_id = get_version_id_from_tag(repo, tag_name)
            self.logger.info(f"Resolved ancestor to version: {spv_id}")
            self.logger.info("")

            return self._convert_ancestor_id(spv_id)
        else:
            raise TaskOptionsError(f"Unrecognized value for ancestor_id: {spv_id}")

    def _convert_ancestor_id(self, ancestor_id: str) -> str:
        """Given a SubscriberPackageVersionId (04t) find
        the corresponding Package2VersionId (05i).
        See: https://github.com/forcedotcom/salesforce-alm/blob/83745351670a701762c6ecc926885564b8853357/src/lib/package/packageUtils.ts#L517

        @param ancestor_id A SubscriberPackageVersionId (04t)
        @returns the corresponding Package2VersionId (05i) or an empty string
        if no Package2Version is found.
        """
        package_2_version_id = ""
        res = self.tooling.query(
            f"SELECT Id FROM Package2Version WHERE SubscriberPackageVersionId='{ancestor_id}'"
        )
        if res["size"] > 0:
            package_2_version_id = res["records"][0]["Id"]
            self.logger.info(
                f"Converted ancestor_id to corresponding Package2Version: {package_2_version_id}"
            )
            self.logger.info("")

        return package_2_version_id

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
                return PackageVersionNumber(
                    **res["records"][0], package_type=PackageType.SECOND_GEN
                )
        elif version_base == "latest_github_release":
            # Get the version of the latest github release
            try:
                # Because we are building a 2GP (which has an incrementable version number)
                # but the latest package version may in fact be a 1GP, force this version number
                # to be treated as a 2GP so we can increment it.
                return PackageVersionNumber.parse(
                    str(self.project_config.get_latest_version()),
                    package_type=PackageType.SECOND_GEN,
                )
            except GithubException:
                # handle case where there isn't a release yet
                pass
        else:
            return PackageVersionNumber.parse(
                version_base, package_type=PackageType.SECOND_GEN
            )
        return PackageVersionNumber(package_type=PackageType.SECOND_GEN)

    def _get_dependencies(self):
        """Resolve dependencies into SubscriberPackageVersionIds (04t prefix)"""
        dependencies = get_static_dependencies(
            self.project_config,
            resolution_strategy=self.options.get("resolution_strategy") or "production",
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
        return any(
            isinstance(dependency, PackageNamespaceVersionDependency)
            and not dependency.version_id
            for dependency in project_dependencies
        )

    def _convert_project_dependencies(self, dependencies):
        """Convert dependencies into the format expected by Package2VersionCreateRequest.

        For dependencies expressed as a GitHub repo subfolder, build an unlocked package from that.
        """
        new_dependencies = []
        for dependency in dependencies:
            new_dependency = {}
            if isinstance(dependency, PackageVersionIdDependency) or (
                isinstance(dependency, PackageNamespaceVersionDependency)
                and dependency.version_id
            ):
                self.logger.info(
                    f"Adding dependency {dependency.package_name} with id {dependency.version_id}"
                )
                new_dependency["subscriberPackageVersionId"] = dependency.version_id
            elif isinstance(dependency, UnmanagedDependency):
                if self.options["create_unlocked_dependency_packages"]:
                    version_id = self._create_unlocked_package_from_unmanaged_dep(
                        dependency, new_dependencies
                    )
                    self.logger.info(
                        f"Adding dependency {dependency} with id {version_id}"
                    )
                    new_dependency["subscriberPackageVersionId"] = version_id
                else:
                    self.logger.info(
                        f"Skipping dependency {dependency} because create_unlocked_dependency_packages is False."
                    )
                    continue
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

        if not self.options["create_unlocked_dependency_packages"]:
            self.logger.info(
                "Skipping unpackaged/pre dependencies because create_unlocked_dependency_packages is False."
            )
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

    def _create_unlocked_package_from_unmanaged_dep(
        self, dependency: UnmanagedDependency, dependencies
    ) -> str:
        if isinstance(dependency, UnmanagedGitHubRefDependency):
            repo_owner, repo_name = split_repo_url(dependency.github)
            package_name = f"{repo_owner}/{repo_name} {dependency.subfolder}"
        else:
            package_name = dependency.description

        package_zip_builder = dependency.get_metadata_package_zip_builder(
            self.project_config, self.org_config
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
        self.logger.info(f"Creating package for dependencies in {path}")
        package_name = (
            f"{self.project_config.repo_owner}/{self.project_config.repo_name} {path}"
        )
        with convert_sfdx_source(path, package_name, self.logger) as src_path:
            package_zip_builder = MetadataPackageZipBuilder(
                path=src_path, name=package_name, context=self.context
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

    def _prepare_cci_dependencies(self, deps) -> List[dict]:
        # Convert the dependencies returned by the Tooling API
        # for the new package back into `update_dependencies`-compatible
        # format for persistence into the GitHub release.

        if deps:
            return [
                PackageVersionIdDependency(
                    version_id=v["subscriberPackageVersionId"]
                ).dict(exclude_none=True)
                for v in deps["ids"]
            ]

        return []
