import time
from datetime import datetime, timedelta

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
        if "namespace" not in self.options:
            self.options["namespace"] = self.project_config.project__package__namespace

    def _run_task(self):
        package_id, package_info = self._get_package_id_and_info()

        self._make_package_upload_request(package_info, package_id)

        if self.upload["Status"] == "ERROR":
            self._handle_package_upload_error()
        else:
            self._handle_package_upload_success(package_id)

    def _get_package_id_and_info(self):
        namespace = self.options["namespace"]
        package = self._get_one_record(
            f"SELECT Id FROM MetadataPackage WHERE NamespacePrefix='{namespace}'",
            f"No package found with namespace {namespace}",
        )
        package_id = package["Id"]
        production = self.options.get("production", False) in [True, "True", "true"]

        package_info = {
            "VersionName": self.options["name"],
            "IsReleaseVersion": production,
            "MetadataPackageId": package_id,
        }
        self._set_package_info_values_from_options(package_info)

        return package_id, package_info

    def _set_package_info_values_from_options(self, package_info):
        if "description" in self.options:
            package_info["Description"] = self.options["description"]
        if "password" in self.options:
            package_info["Password"] = self.options["password"]
        if "post_install_url" in self.options:
            package_info["PostInstallUrl"] = self.options["post_install_url"]
        if "release_notes_url" in self.options:
            package_info["ReleaseNotesUrl"] = self.options["release_notes_url"]

    def _make_package_upload_request(self, package_info, package_id):
        """Creates a PackageUploadRequest in self.upload"""
        PackageUploadRequest = self._get_tooling_object("PackageUploadRequest")

        start_time = time.time()
        self.upload = PackageUploadRequest.create(package_info)
        self._upload_time_seconds = time.time() - start_time

        self.upload_id = self.upload["id"]
        self.logger.info(
            "Created PackageUploadRequest {} for Package {}".format(
                self.upload_id, package_id
            )
        )
        self._poll()

    def _handle_package_upload_error(self):
        self.logger.error("Package upload failed with the following errors")
        error = {"message": ""}
        apex_test_failures = False
        for error in self.upload["Errors"]["errors"]:
            self.logger.error("  {}".format(error["message"]))
            if error["message"] == "ApexTestFailure":
                apex_test_failures = True

        if apex_test_failures:
            self._display_apex_test_failures()

        exception = self._get_exception_type(error)
        raise exception("Package upload failed")

    def _display_apex_test_failures(self):
        self.logger.error("Failed Apex Tests:")
        soql_query = self._get_failed_tests_soql_query()
        results = self.tooling.query(soql_query)
        for test in results["records"]:
            self.logger.error(f"    {test['ApexClass']['Name']}.{test['MethodName']}")

    def _get_failed_tests_soql_query(self):
        package_upload_datetime = self._get_package_upload_iso_timestamp()
        return (
            "SELECT ApexClass.Name, "
            "MethodName, "
            "Message "
            "FROM ApexTestResult "
            "WHERE Outcome='Fail' "
            f"AND TestTimestamp > {package_upload_datetime}"
        )

    def _get_package_upload_iso_timestamp(self):
        """Returns a datetime of approximately when package upload began
        This assumes a short time between the call to
        _make_package_upload_request() and this function"""
        test_start_datetime = datetime.utcnow() - timedelta(
            seconds=self._upload_time_seconds
        )
        return test_start_datetime.isoformat()

    def _get_exception_type(self, error):
        return (
            ApexTestException
            if error["message"] == "ApexTestFailure"
            else SalesforceException
        )

    def _handle_package_upload_success(self, package_id):
        self._set_package_version_values()

        self.return_values = {
            "version_number": str(self.version_number),
            "version_id": self.version_id,
            "package_id": package_id,
        }

        self.logger.info(
            "Uploaded package version {} with Id {}".format(
                self.version_number, self.version_id
            )
        )

    def _set_package_version_values(self):
        """Sets version_id and version_number on self.
        Assumes that self.upload['Status'] was a success"""
        self.version_id = self.upload["MetadataPackageVersionId"]
        version = self._get_one_record(
            (
                "SELECT MajorVersion, "
                "MinorVersion, "
                "PatchVersion, "
                "BuildNumber, "
                "ReleaseState "
                "FROM MetadataPackageVersion "
                f"WHERE Id='{self.version_id}'"
            ),
            f"Version {self.version_id} not found",
        )
        version_parts = [str(version["MajorVersion"]), str(version["MinorVersion"])]
        if version["PatchVersion"]:
            version_parts.append(str(version["PatchVersion"]))

        self.version_number = ".".join(version_parts)

        if version["ReleaseState"] == "Beta":
            self.version_number += f" (Beta {version['BuildNumber']})"

    def _get_one_record(self, query, message):
        result = self.tooling.query(query)
        if result["totalSize"] != 1:
            self.logger.error(message)
            raise SalesforceException(message)
        return result["records"][0]

    def _poll_action(self):
        soql_check_upload = (
            "SELECT Id, "
            "Status, "
            "Errors, "
            "MetadataPackageVersionId "
            "FROM PackageUploadRequest "
            f"WHERE Id = '{self.upload_id}'"
        )
        self.upload = self._get_one_record(
            soql_check_upload, f"Failed to get info for upload with id {self.upload_id}"
        )
        self.logger.info(
            "PackageUploadRequest {} is {}".format(
                self.upload_id, self.upload["Status"]
            )
        )

        self.poll_complete = not self._poll_again(self.upload["Status"])

    def _poll_again(self, upload_status):
        return upload_status in ["IN_PROGRESS", "QUEUED"]
