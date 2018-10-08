from builtins import str
from cumulusci.core.exceptions import ApexTestException
from cumulusci.core.exceptions import SalesforceException
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class PackageUpload(BaseSalesforceApiTask):
    name = "PackageUpload"
    api_version = "38.0"
    task_options = {
        "name": {"description": "The name of the package version.", "required": True},
        "production": {
            "description": "If True, uploads a production release.  Defaults to uploading a beta"
        },
        "description": {
            "description": "A description of the package and what this version contains."
        },
        "password": {
            "description": "An optional password for sharing the package privately with anyone who has the password. Don't enter a password if you want to make the package available to anyone on AppExchange and share your package publicly."
        },
        "post_install_url": {
            "description": "The fully-qualified URL of the post-installation instructions. Instructions are shown as a link after installation and are available from the package detail view."
        },
        "release_notes_url": {
            "description": "The fully-qualified URL of the package release notes. Release notes are shown as a link during the installation process and are available from the package detail view after installation."
        },
        "namespace": {
            "description": "The namespace of the package.  Defaults to project__package__namespace"
        },
    }

    def _init_options(self, kwargs):
        super(PackageUpload, self)._init_options(kwargs)

        self.upload = None
        self.upload_id = None

        # Set the namespace option to the value from cumulusci.yml if not already set
        if not "namespace" in self.options:
            self.options["namespace"] = self.project_config.project__package__namespace

    def _run_task(self):
        package = self._get_one(
            "select Id from MetadataPackage where NamespacePrefix='{}'".format(
                self.options["namespace"]
            ),
            "No package found with namespace {}".format(self.options["namespace"]),
        )
        package_id = package["Id"]

        production = self.options.get("production", False) in [True, "True", "true"]
        package_info = {
            "VersionName": self.options["name"],
            "IsReleaseVersion": production,
            "MetadataPackageId": package_id,
        }

        if "description" in self.options:
            package_info["Description"] = self.options["description"]
        if "password" in self.options:
            package_info["Password"] = self.options["password"]
        if "post_install_url" in self.options:
            package_info["PostInstallUrl"] = self.options["post_install_url"]
        if "release_notes_url" in self.options:
            package_info["ReleaseNotesUrl"] = self.options["release_notes_url"]

        PackageUploadRequest = self._get_tooling_object("PackageUploadRequest")
        self.upload = PackageUploadRequest.create(package_info)
        self.upload_id = self.upload["id"]

        self.logger.info(
            "Created PackageUploadRequest {} for Package {}".format(
                self.upload_id, package_id
            )
        )
        self._poll()

        if self.upload["Status"] == "ERROR":
            self.logger.error("Package upload failed with the following errors")
            error = {"message": ""}
            for error in self.upload["Errors"]["errors"]:
                self.logger.error("  {}".format(error["message"]))

            # use the last error in the batch, but log them all.
            error_class = (
                ApexTestException
                if error["message"] == "ApexTestFailure"
                else SalesforceException
            )
            raise error_class("Package upload failed")
        else:
            version_id = self.upload["MetadataPackageVersionId"]
            version = self._get_one(
                "select MajorVersion, MinorVersion, PatchVersion, BuildNumber, ReleaseState from MetadataPackageVersion where Id = '{}'".format(
                    version_id
                ),
                "Version {} not found".format(version_id),
            )
            version_parts = [str(version["MajorVersion"]), str(version["MinorVersion"])]
            if version["PatchVersion"]:
                version_parts.append(str(version["PatchVersion"]))

            self.version_number = ".".join(version_parts)

            if version["ReleaseState"] == "Beta":
                self.version_number += " (Beta {})".format(version["BuildNumber"])

            self.return_values = {
                "version_number": str(self.version_number),
                "version_id": version_id,
                "package_id": package_id,
            }

            self.logger.info(
                "Uploaded package version {} with Id {}".format(
                    self.version_number, version_id
                )
            )

    def _get_one(self, query, message):
        result = self.tooling.query(query)
        if result["totalSize"] != 1:
            self.logger.error(message)
            raise SalesforceException(message)
        return result["records"][0]

    def _poll_action(self):
        soql_check_upload = "select Id, Status, Errors, MetadataPackageVersionId from PackageUploadRequest where Id = '{}'".format(
            self.upload_id
        )
        self.upload = self._get_one(
            soql_check_upload,
            "Failed to get info for upload with id {}".format(self.upload_id),
        )
        self.logger.info(
            "PackageUploadRequest {} is {}".format(
                self.upload_id, self.upload["Status"]
            )
        )

        self.poll_complete = not self._poll_again(self.upload["Status"])

    def _poll_again(self, upload_status):
        return upload_status in ["IN_PROGRESS", "QUEUED"]
