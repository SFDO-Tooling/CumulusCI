from typing import Optional
import base64
import enum
import io
import json
import pathlib
import zipfile

from pydantic import BaseModel, validator
from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.exceptions import DependencyLookupError
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import PackageUploadFailure
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.package_zip import BasePackageZipBuilder
from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.salesforce.org_settings import build_settings_package
from cumulusci.utils import download_extract_github


class PackageTypeEnum(str, enum.Enum):
    managed = "Managed"
    unlocked = "Unlocked"


class VersionTypeEnum(str, enum.Enum):
    major = "major"
    minor = "minor"
    patch = "patch"


class PackageConfig(BaseModel):
    package_name: str
    description: str = ""
    package_type: PackageTypeEnum
    org_dependent: bool = False
    namespace: Optional[str]
    branch: Optional[str] = None
    version_name: str
    version_type: VersionTypeEnum = VersionTypeEnum.minor

    @validator("org_dependent")
    def org_dependent_must_be_unlocked(cls, v, values):
        if v and values["package_type"] != PackageTypeEnum.unlocked:
            raise ValueError("Only unlocked packages can be org-dependent.")
        return v


class CreatePackageVersion(BaseSalesforceApiTask):
    """Creates a new second-generation package version.

    If a package named ``package_name`` does not yet exist in the Dev Hub, it will be created.
    """

    api_version = "49.0"

    task_options = {
        "package_name": {"description": "Name of package"},
        "package_type": {
            "description": "Package type (Unlocked or Managed)",
            "required": True,
        },
        "namespace": {"description": "Package namespace"},
        "version_name": {"description": "Version name"},
        "version_type": {
            "description": "The part of the version number to increment. "
            "Options are major, minor, patch.  Defaults to minor"
        },
        "dependency_org": {
            "description": "The org name of the org to use for project dependencies lookup. If not provided, a scratch org will be created with the org name 2gp_dependencies."
        },
        "skip_validation": {
            "description": "If true, skip validation of the package version. Default: false. "
            "Skipping validation creates packages more quickly, but they cannot be promoted for release."
        },
        "org_dependent": {
            "description": "If true, create an org-dependent unlocked package. Default: false."
        },
        "force_upload": {
            "description": "If true, force creating a new package version even if one with the same contents already exists"
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
            namespace=self.options.get("namespace")
            or self.project_config.project__package__namespace,
            branch=self.project_config.repo_branch,
            version_name=self.options.get("version_name") or "Release",
            version_type=self.options.get("version_type") or "minor",
        )
        self.options["skip_validation"] = process_bool_arg(
            self.options.get("skip_validation", False)
        )
        self.options["force_upload"] = process_bool_arg(
            self.options.get("force_upload", False)
        )

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
        package_zip_builder = MetadataPackageZipBuilder(
            path=self.project_config.default_package_path,
            name=self.package_config.package_name,
            options={"package_type": self.package_config.package_type.value},
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
        self.return_values["version_number"] = self._get_version_number(
            package2_version
        )

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
            # @@@ we should support releasing a successor to an older version by specifying a base version
            last_version_parts = self._get_highest_version_parts(package_id)
            version_number = self._get_next_version_number(
                last_version_parts, package_config.version_type
            )
            package_descriptor = {
                "ancestorId": "",  # @@@ need to add this for Managed 2gp
                "id": package_id,
                "path": "",
                "versionName": package_config.version_name,
                "versionNumber": version_number,
            }

            # Add org shape
            try:
                dev_org_config = self.project_config.keychain.get_org("dev")
            except OrgNotFound:
                pass
            else:
                with open(dev_org_config.config_file, "r") as f:
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
            if not package_config.org_dependent and not is_dependency:
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
            "Branch": package_config.branch,
            "Package2Id": package_id,
            "SkipValidation": skip_validation,
            "Tag": f"hash:{package_hash}",
            "VersionInfo": version_info,
        }
        self.logger.info(
            f"Requesting creation of package version {version_number} "
            f"for package {package_config.package_name} ({package_id})"
        )
        response = Package2CreateVersionRequest.create(request)
        self.logger.info(
            f"Package2VersionCreateRequest created with id {response['id']}"
        )
        return response["id"]

    def _get_highest_version_parts(self, package_id):
        """Get the version parts for the highest existing version of the specified package."""
        res = self.tooling.query(
            "SELECT MajorVersion, MinorVersion, PatchVersion, BuildNumber, IsReleased "
            "FROM Package2Version "
            f"WHERE Package2Id='{package_id}' "
            "ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion DESC, BuildNumber DESC "
            "LIMIT 1"
        )
        if res["size"]:
            return res["records"][0]
        return {
            "MajorVersion": 0,
            "MinorVersion": 0,
            "PatchVersion": 0,
            "BuildNumber": 0,
            "IsReleased": False,
        }

    def _get_next_version_number(self, version_parts, version_type: VersionTypeEnum):
        """Predict the next package version.

        Given existing version parts (major/minor/patch) and a version type,
        determine the number to request for the next version.
        """
        new_version_parts = {
            "MajorVersion": version_parts["MajorVersion"],
            "MinorVersion": version_parts["MinorVersion"],
            "PatchVersion": version_parts["PatchVersion"],
            "BuildNumber": "NEXT",
        }
        if version_parts["IsReleased"]:
            if version_type == VersionTypeEnum.major:
                new_version_parts["MajorVersion"] += 1
                new_version_parts["MinorVersion"] = 0
                new_version_parts["PatchVersion"] = 0
            if version_type == VersionTypeEnum.minor:
                new_version_parts["MinorVersion"] += 1
                new_version_parts["PatchVersion"] = 0
            elif version_type == VersionTypeEnum.patch:
                new_version_parts["PatchVersion"] += 1
        return self._get_version_number(new_version_parts)

    def _get_version_number(self, version):
        """Format version fields from Package2Version as a version number."""
        return "{MajorVersion}.{MinorVersion}.{PatchVersion}.{BuildNumber}".format(
            **version
        )

    def _get_dependencies(self):
        """Resolve dependencies into SubscriberPackageVersionIds (04t prefix)"""
        dependencies = self.project_config.get_static_dependencies()

        # If any dependencies are expressed as a 1gp namespace + version,
        # we need to convert those to 04t package version ids,
        # for which we need an org with the packages installed.
        if self._has_1gp_namespace_dependency(dependencies):
            org = self._get_dependency_org()
            dependencies = org.resolve_04t_dependencies(dependencies)

        # Convert dependencies to correct format for Package2VersionCreateRequest
        dependencies = self._convert_project_dependencies(dependencies)

        # Build additional packages for local unpackaged/pre
        dependencies = self._get_unpackaged_pre_dependencies(dependencies)

        return dependencies

    def _has_1gp_namespace_dependency(self, project_dependencies):
        """Returns true if any dependencies are specified using a namespace rather than 04t"""
        for dependency in project_dependencies:
            if "namespace" in dependency:
                return True
            if "dependencies" in dependency:
                if self._has_1gp_namespace_dependency(dependency["dependencies"]):
                    return True
        return False

    def _get_dependency_org(self):
        """Get a scratch org that we can use to look up subscriber package version ids.

        If the `dependency_org` option is specified, use it.
        Otherwise create a new org named `2gp_dependencies` and run the `dependencies` flow.
        """
        org_name = self.options.get("dependency_org")
        if org_name:
            org = self.project_config.keychain.get_org(org_name)
        else:
            org_name = "2gp_dependencies"
            if org_name not in self.project_config.keychain.orgs:
                self.project_config.keychain.create_scratch_org(
                    "2gp_dependencies", "dev"
                )

            org = self.project_config.keychain.get_org("2gp_dependencies")
            if org.created and org.expired:
                self.logger.info(
                    "Recreating expired scratch org named 2gp_dependencies to resolve dependency package version ids"
                )
                org.create_org()
                self.project_config.keychain.set_org(org)
            elif org.created:
                self.logger.info(
                    "Using existing scratch org named 2gp_dependencies to resolve dependency package version ids"
                )
            else:
                self.logger.info(
                    "Creating a new scratch org with the name 2gp_dependencies to resolve dependency package version ids"
                )

            self.logger.info(
                "Running the dependencies flow against the 2gp_dependencies scratch org"
            )
            coordinator = FlowCoordinator(
                self.project_config, self.project_config.get_flow("dependencies")
            )
            coordinator.run(org)

        return org

    def _convert_project_dependencies(self, dependencies):
        """Convert dependencies into the format expected by Package2VersionCreateRequest.

        For dependencies expressed as a github repo subfolder, build an unlocked package from that.
        """
        new_dependencies = []
        for dependency in dependencies:
            if dependency.get("dependencies"):
                new_dependencies.extend(
                    self._convert_project_dependencies(dependency["dependencies"])
                )

            new_dependency = {}
            if dependency.get("version_id"):
                name = (
                    f"{dependency['namespace']}@{dependency['version']} "
                    if "namespace" in dependency
                    else ""
                )
                self.logger.info(
                    f"Adding dependency {name} with id {dependency['version_id']}"
                )
                new_dependency["subscriberPackageVersionId"] = dependency["version_id"]

            elif dependency.get("repo_name"):
                version_id = self._create_unlocked_package_from_github(
                    dependency, new_dependencies
                )
                self.logger.info(
                    "Adding dependency {}/{} {} with id {}".format(
                        dependency["repo_owner"],
                        dependency["repo_name"],
                        dependency["subfolder"],
                        version_id,
                    )
                )
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
            dependency["repo_owner"], dependency["repo_name"]
        )
        zip_src = download_extract_github(
            gh_for_repo,
            dependency["repo_owner"],
            dependency["repo_name"],
            dependency["subfolder"],
            ref=dependency.get("ref"),
        )
        package_zip_builder = MetadataPackageZipBuilder.from_zipfile(
            zip_src, options=dependency, logger=self.logger
        )

        package_config = PackageConfig(
            package_name="{repo_owner}/{repo_name} {subfolder}".format(**dependency),
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
