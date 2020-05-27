from typing import Optional
import base64
import enum
import hashlib
import io
import json
import os
import zipfile

from pydantic import BaseModel

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import DependencyLookupError
from cumulusci.core.exceptions import PackageUploadFailure
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.utils import cd
from cumulusci.utils import download_extract_github
from cumulusci.utils import temporary_dir
from cumulusci.utils import inject_namespace
from cumulusci.utils import strip_namespace
from cumulusci.utils import tokenize_namespace


class PackageTypeEnum(str, enum.Enum):
    managed = "Managed"
    unlocked = "Unlocked"


class SourceFormatEnum(str, enum.Enum):
    sfdx = "sfdx"
    mdapi = "mdapi"


class VersionTypeEnum(str, enum.Enum):
    major = "major"
    minor = "minor"
    patch = "patch"


class PackageConfig(BaseModel):
    name: str
    package_type: PackageTypeEnum = PackageTypeEnum.managed
    namespace: Optional[str]
    source_format: SourceFormatEnum = SourceFormatEnum.sfdx
    source_path: str
    branch: str
    version_name: VersionTypeEnum = VersionTypeEnum.minor


class CreatePackageVersion(BaseSalesforceApiTask):
    """Creates a new second-generation package version.

    If a package named ``package_name`` does not yet exist in the Dev Hub, it will be created.
    """

    task_options = {
        "package_name": {"description": "Name of package"},
        "package_type": {
            "description": "Package type (unlocked or managed)",
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
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        source_format = self.project_config.project__package__source_format or "sfdx"
        self.package_config = PackageConfig(
            name=self.options.get("name") or self.project_config.project__package__name,
            package_type=self.options.get("package_type"),
            namespace=self.options.get("namespace"),
            source_format=source_format,
            # @@@ use default package directory for sfdx format
            source_path="src"
            if source_format == SourceFormatEnum.mdapi
            else "force-app",
            version_name=self.options.get("version_name"),
            version_type=self.options.get("version_type") or "minor",
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
        self.request_id = self._create_version_request(
            self.package_id, self.package_config
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
        subscriber_version = res["records"][0]
        self.return_values["dependencies"] = subscriber_version["Dependencies"]

        self.logger.info("Return Values: {}".format(self.return_values))

    def _get_or_create_package(self, package_config: PackageConfig):
        """Find or create the Package2

        Checks the Dev Hub for an existing, non-deprecated 2GP package
        with matching name, type, and namespace.
        """
        query = f"SELECT Id FROM Package2 WHERE IsDeprecated = FALSE AND ContainerOptions='{package_config.package_type}' AND Name='{package_config.name}'"
        if package_config.namespace:
            query += f" AND NamespacePrefix='{package_config.namespace}'"
        else:
            query += " AND NamespacePrefix=null"
        res = self.tooling.query(query)
        if res["size"] > 1:
            raise TaskOptionsError(
                f"Found {res['size']} packages with the same name, namespace, and package_type"
            )
        if res["size"] == 1:
            return res["records"][0]["Id"]

        self.logger.info("No existing package found, creating the package")
        Package2 = self._get_tooling_object("Package2")
        package = Package2.create(
            {
                "ContainerOptions": package_config.package_type,
                "Name": package_config.name,
                "NamespacePrefix": package_config.namespace,
            }
        )
        return package["id"]

    def _create_version_request(self, package_id, package_config):
        # Prepare the VersionInfo file
        version_bytes = io.BytesIO()
        version_info = zipfile.ZipFile(version_bytes, "w", zipfile.ZIP_DEFLATED)

        # Zip up the packaged metadata
        package_bytes = io.BytesIO()
        package_zip = zipfile.ZipFile(package_bytes, "w", zipfile.ZIP_DEFLATED)
        if package_config.source_format == SourceFormatEnum.sfdx:
            self.logger.info("Converting from sfdx to mdapi format")
            with temporary_dir(chdir=False) as path:
                # @@@ use sfdx helper instead of task
                task_config = TaskConfig(
                    {
                        "options": {
                            "command": f"force:source:convert -d {path} -r {package_config.source_path} -n '{package_config.name}'"
                        }
                    }
                )
                self.logger.info("cwd: {}".format(os.getcwd()))
                task = SFDXBaseTask(self.project_config, task_config)
                task()
                self._add_files_to_package(package_zip, path)
        else:
            self._add_files_to_package(package_zip, package_config.source_path)
        package_zip.close()
        # @@@ refactor _process_zip_file out of Deploy
        package_zip_processed = self._process_zip_file(zipfile.ZipFile(package_bytes))
        package_zip_processed.close()

        # Add the package.zip to version_info
        version_info.writestr("package.zip", package_bytes.getvalue())

        # Get a hash of the package.zip file
        package_hash = hashlib.blake2b(package_bytes.getvalue()).hexdigest()

        # Check for an existing package with the same contents
        res = self.tooling.query(
            "SELECT Id "
            "FROM Package2VersionCreateRequest "
            "WHERE Package2Id = '{}' "
            "AND Status != 'Error' "
            "AND Tag = 'hash:{}'".format(package_id, package_hash)
        )
        if res["size"] > 0:
            self.logger.info(
                "Found existing request for package with the same metadata.  Using existing package."
            )
            return res["records"][0]["Id"]

        # Create the package2-descriptor.json contents and write to version_info
        # @@@ what if it's based on an older version?
        version_number = self._get_next_version_number(
            package_id, package_config.version_type
        )
        package_descriptor = {
            "ancestorId": "",  # @@@
            "id": package_id,
            "path": package_config.source_path,
            "versionName": package_config.version_name,
            "versionNumber": version_number,
        }

        # Get the dependencies for the package
        is_dependency = package_config is not self.package_config
        if not is_dependency:
            self.logger.info("Determining dependencies for package")
            dependencies = self._get_dependencies()
            if dependencies:
                package_descriptor["dependencies"] = dependencies

        # Finish constructing the request
        version_info.writestr(
            "package2-descriptor.json", json.dumps(package_descriptor)
        )
        version_info.close()
        version_info = base64.b64encode(version_bytes.getvalue()).decode("utf-8")
        Package2CreateVersionRequest = self._get_tooling_object(
            "Package2VersionCreateRequest"
        )
        request = {
            "Branch": package_config.branch,
            "Package2Id": package_id,
            "Tag": f"hash:{package_hash}",
            "VersionInfo": version_info,
        }
        response = Package2CreateVersionRequest.create(request)
        return response["id"]

    def _add_files_to_package(self, package_zip, path):
        with cd(path):
            # @@@ factor out of Deploy
            for file_to_package in self._get_files_to_package():
                package_zip.write(file_to_package)

    def _get_next_version_number(self, package_id, version_type: VersionTypeEnum):
        """Predict the next package version.

        Given a package id and version type (major/minor/patch),
        we query the Dev Hub org for the highest version, then increment.
        """
        res = self.tooling.query(
            "SELECT MajorVersion, MinorVersion, PatchVersion, BuildNumber, IsReleased "
            "FROM Package2Version "
            f"WHERE Package2Id='{package_id}' "
            "ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion DESC, BuildNumber DESC "
            "LIMIT 1"
        )
        if res["size"] == 0:  # No existing version
            version_parts = {
                "MajorVersion": 1 if version_type == VersionTypeEnum.major else 0,
                "MinorVersion": 1 if version_type == VersionTypeEnum.minor else 0,
                "PatchVersion": 1 if version_type == VersionTypeEnum.patch else 0,
                "BuildNumber": "NEXT",
            }
            return self._get_version_number(version_parts)
        last_version = res["records"][0]
        version_parts = {
            "MajorVersion": last_version["MajorVersion"],
            "MinorVersion": last_version["MinorVersion"],
            "PatchVersion": last_version["PatchVersion"],
            "BuildNumber": "NEXT",
        }
        if last_version["IsReleased"] is True:
            if version_type == VersionTypeEnum.major:
                version_parts["MajorVersion"] += 1
                version_parts["MinorVersion"] = 0
                version_parts["PatchVersion"] = 0
            if version_type == VersionTypeEnum.minor:
                version_parts["MinorVersion"] += 1
                version_parts["PatchVersion"] = 0
            elif version_type == VersionTypeEnum.patch:
                version_parts["PatchVersion"] += 1
        return self._get_version_number(version_parts)

    def _get_version_number(self, version):
        """Format version fields from Package2Version as a version number."""
        return "{MajorVersion}.{MinorVersion}.{PatchVersion}.{BuildNumber}".format(
            **version
        )

    def _get_dependencies(self):
        """Resolve dependencies into SubscriberPackageVersionIds (04t prefix)"""
        dependencies = []

        # @@@ change this to return 04ts if available, and use them
        project_dependencies = self.project_config.get_static_dependencies()

        if self._has_1gp_namespace_dependency(project_dependencies):
            # we need to install the dependencies into an org using InstalledPackage metadata
            # in order to look up the subscriber package version ids
            org = self._get_dependency_org()
            installed_dependencies = self._get_installed_dependencies(org)
            dependencies.extend(
                self._convert_project_dependencies(
                    project_dependencies, installed_dependencies
                )
            )

        # Build additional packages for unpackaged/pre
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
                    "Recreating expired scratch org named 2gp_dependencies to resolve package dependencies"
                )
                org.create_org()
                self.project_config.keychain.set_org("2gp_dependencies", org)
            elif org.created:
                self.logger.info(
                    "Using existing scratch org named 2gp_dependencies to resolve dependencies"
                )
            else:
                self.logger.info(
                    "Creating a new scratch org with the name 2gp_dependencies to resolve dependencies"
                )

            # @@@ should use update_dependencies task
            self.logger.info(
                "Running the dependencies flow against the 2gp_dependencies scratch org"
            )
            coordinator = FlowCoordinator(
                self.project_config, self.project_config.get_flow("dependencies")
            )
            coordinator.run(org)

        return org
        # @@@ delete org

    def _get_installed_dependencies(self, org):
        """Get subscriber package version ids from packages installed in an org.
        """
        self.logger.info(
            "Querying installed package version ids in org {}".format(org.name)
        )
        installed_versions = self.tooling.query(
            "SELECT "
            "SubscriberPackage.Id, "
            "SubscriberPackage.Name, "
            "SubscriberPackage.NamespacePrefix, "
            "SubscriberPackageVersion.Id, "
            "SubscriberPackageVersion.Name, "
            "SubscriberPackageVersion.MajorVersion, "
            "SubscriberPackageVersion.MinorVersion, "
            "SubscriberPackageVersion.PatchVersion, "
            "SubscriberPackageVersion.BuildNumber, "
            "SubscriberPackageVersion.IsBeta, "
            "SubscriberPackageVersion.IsManaged "
            "FROM InstalledSubscriberPackage"
        )

        installed_dependencies = {}
        if installed_versions["size"] > 0:
            for installed in installed_versions["records"]:
                if installed["SubscriberPackage"]["NamespacePrefix"] is None:
                    continue
                version_str = "{MajorVersion}.{MinorVersion}".format(
                    **installed["SubscriberPackageVersion"]
                )
                if installed["SubscriberPackageVersion"]["PatchVersion"]:
                    version_str += (
                        "." + installed["SubscriberPackageVersion"]["PatchVersion"]
                    )
                if installed["SubscriberPackageVersion"]["IsBeta"]:
                    version_str += (
                        f" (Beta {installed['SubscriberPackageVersion']['BuildNumber']}"
                    )

                # Note: SubscriberPackageVersions can be from 2gp packages,
                # in which case there can be multiple packages with the same namespace.
                # But we're only using this info to look up 04ts for 1gp packages,
                # and it's not possible to install a 2gp if the org already
                # has a 1gp with the same namespace,
                # so it's okay to use namespace in the key here.
                installed_dependencies[
                    installed["SubscriberPackage"]["NamespacePrefix"]
                    + "@"
                    + version_str
                ] = {
                    "package_id": installed["SubscriberPackage"]["Id"],
                    "package_name": installed["SubscriberPackage"]["Name"],
                    "version_id": installed["SubscriberPackageVersion"]["Id"],
                    "version_name": installed["SubscriberPackageVersion"]["Name"],
                }
        return installed_dependencies

    def _convert_project_dependencies(
        self, project_dependencies, installed_dependencies
    ):
        """Convert dependencies into the format expected by Package2VersionCreateRequest.

        At a high level this means finding a 04t subscriber package version id for each one.

        If we have a namespace and version, we can find the 04t from an org where the package is installed.
        If we have a github repo, we can build an unlocked package from that.
        """
        # @@@ refactor so that getting installed packages happens from here?
        dependencies = []
        for dependency in project_dependencies:
            dependency_info = {}
            if dependency.get("namespace"):
                version_info = installed_dependencies.get(
                    "{namespace}@{version}".format(**dependency)
                )
                if not version_info:
                    raise DependencyLookupError(
                        "Could not find installed dependency in org: {namespace}@{version}".format(
                            **dependency
                        )
                    )
                self.logger.info(
                    "Adding dependency {}@{} with id {}".format(
                        dependency["namespace"],
                        dependency["version"],
                        version_info["version_id"],
                    )
                )
                dependency_info["subscriberPackageVersionId"] = version_info[
                    "version_id"
                ]

            if dependency.get("repo_name"):
                if dependency.get("subfolder", "").startswith("unpackaged/post"):
                    continue
                version_id = self._create_package_from_github(dependency)
                self.logger.info(
                    "Adding dependency {}/{} {} with id {}".format(
                        dependency["repo_owner"],
                        dependency["repo_name"],
                        dependency["subfolder"],
                        version_id,
                    )
                )
                dependency_info["subscriberPackageVersionId"] = version_id

            if dependency.get("dependencies"):
                # @@@ do these need to go at the start of the list?
                dependencies.extend(
                    self._convert_project_dependencies(
                        dependency["dependencies"], installed_dependencies
                    )
                )

            dependencies.append(dependency_info)

        return dependencies

    def _get_unpackaged_pre_dependencies(self, dependencies):
        """Create package for unpackaged/pre metadata, if necessary
        """
        path = "unpackaged/pre"
        # @@@ factor out util for iterating over subfolders
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if not os.path.isdir(item_path):
                continue
            version_id = self._create_package_from_local(item_path)
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

    def _create_package_from_github(self, dependency):
        # @@@ This is yanked and slightly modified from UpdateDependencies and should be refactored out to somewhere reusable between both tasks
        gh_for_repo = self.project_config.get_github_api(
            dependency["repo_owner"], dependency["repo_name"]
        )
        package_zip = download_extract_github(
            gh_for_repo,
            dependency["repo_owner"],
            dependency["repo_name"],
            dependency["subfolder"],
            ref=dependency.get("ref"),
        )

        if dependency.get("namespace_tokenize"):
            self.logger.info(
                "Replacing namespace prefix {}__ in files and filenames with namespace token strings".format(
                    "{}__".format(dependency["namespace_tokenize"])
                )
            )
            package_zip = zip_tokenize_namespace(
                package_zip,
                namespace=dependency["namespace_tokenize"],
                logger=self.logger,
            )

        if dependency.get("namespace_inject"):
            self.logger.info(
                "Replacing namespace tokens with {}".format(
                    "{}__".format(dependency["namespace_inject"])
                )
            )
            package_zip = zip_inject_namespace(
                package_zip,
                namespace=dependency["namespace_inject"],
                managed=not dependency.get("unmanaged"),
                namespaced_org=self.options["namespaced_org"],
                logger=self.logger,
            )

        if dependency.get("namespace_strip"):
            self.logger.info(
                "Removing namespace prefix {}__ from all files and filenames".format(
                    "{}__".format(dependency["namespace_strip"])
                )
            )
            package_zip = zip_strip_namespace(
                package_zip, namespace=dependency["namespace_strip"], logger=self.logger
            )

        # @@@ make it possible to pass existing package zip into _create_version_request
        # so we don't have to extract it
        with temporary_dir() as path:
            with cd(path):
                package_zip.extractall(path)
                package_config = {
                    "name": "{repo_owner}/{repo_name} {subfolder}".format(**dependency),
                    "version_name": "{repo_owner}/{repo_name} {subfolder} - ".format(
                        **dependency
                    )
                    + "{{ version }}",
                    "package_type": "unlocked",
                    "path": os.path.join(path),
                    # @@@ Ideally we'd do this without a namespace but that causes package creation errors
                    "namespace": self.package_config.get("namespace"),
                }
                package_id = self._get_or_create_package(package_config)
                self.request_id = self._create_version_request(
                    package_id, package_config
                )

        self._poll()
        # @@@ don't need all these fields
        res = self.tooling.query(
            "SELECT "
            "MajorVersion, "
            "MinorVersion, "
            "PatchVersion, "
            "BuildNumber, "
            "SubscriberPackageVersionId "
            "FROM Package2Version "
            "WHERE Id='{}' ".format(self.package_version_id)
        )
        package2_version = res["records"][0]

        return package2_version["SubscriberPackageVersionId"]

    def _create_package_from_local(self, path):
        """Create an unlocked package version from a local directory."""
        self.logger.info("Creating package for dependencies in {}".format(path))
        package_name = "{}/{} {}".format(
            self.project_config.repo_owner, self.project_config.repo_name, path
        )
        package_config = {
            "name": package_name,
            "version_name": package_name + "{{ version }}",
            "package_type": "unlocked",
            "path": path,
            # @@@ Ideally we'd do this without a namespace but that causes package creation errors
            "namespace": self.package_config.get("namespace"),
        }
        package_id = self._get_or_create_package(package_config)
        self.request_id = self._create_version_request(package_id, package_config)
        self._poll()
        self.poll_complete = False
        # @@@ don't need all these fields
        res = self.tooling.query(
            "SELECT "
            "MajorVersion, "
            "MinorVersion, "
            "PatchVersion, "
            "BuildNumber, "
            "SubscriberPackageVersionId "
            "FROM Package2Version "
            "WHERE Id='{}' ".format(self.package_version_id)
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
        elif request["Status"] in ("Queued", "InProgress"):
            self.logger.info(
                f"[{request['Status']}: Checking status of Package2VersionCreateRequest {request['Id']}"
            )
