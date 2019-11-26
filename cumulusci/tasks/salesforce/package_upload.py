from datetime import datetime

from cumulusci.core.exceptions import ApexTestException
from cumulusci.core.exceptions import SalesforceException
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.cli.ui import CliTable


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
        self.package_id = None

        # Set the namespace option to the value from cumulusci.yml if not already set
        if "namespace" not in self.options:
            self.options["namespace"] = self.project_config.project__package__namespace

    def _run_task(self):
        self._set_package_id()
        self._set_package_info()

        self._make_package_upload_request()

        if self.upload["Status"] == "ERROR":
            self._log_package_upload_errors()
        else:
            self._set_package_version_values_on_self()
            self._set_return_values()
            self._log_package_upload_success()

    def _set_package_info(self):
        if not self.package_id:
            self._set_package_id()

        production = self.options.get("production", False) in [True, "True", "true"]

        self.package_info = {
            "VersionName": self.options["name"],
            "IsReleaseVersion": production,
            "MetadataPackageId": self.package_id,
        }

        if "description" in self.options:
            self.package_info["Description"] = self.options["description"]
        if "password" in self.options:
            self.package_info["Password"] = self.options["password"]
        if "post_install_url" in self.options:
            self.package_info["PostInstallUrl"] = self.options["post_install_url"]
        if "release_notes_url" in self.options:
            self.package_info["ReleaseNotesUrl"] = self.options["release_notes_url"]

    def _set_package_id(self):
        namespace = self.options["namespace"]
        package = self._get_one_record(
            f"SELECT Id FROM MetadataPackage WHERE NamespacePrefix='{namespace}'",
            f"No package found with namespace {namespace}",
        )
        self.package_id = package["Id"]

    def _make_package_upload_request(self):
        """Creates a PackageUploadRequest in self.upload"""
        PackageUploadRequest = self._get_tooling_object("PackageUploadRequest")

        self._upload_start_time = datetime.utcnow()
        self.upload = PackageUploadRequest.create(self.package_info)

        self.upload_id = self.upload["id"]
        self.logger.info(
            f"Created PackageUploadRequest {self.upload_id} for Package {self.package_id}"
        )
        self._poll()

    def _log_package_upload_errors(self):
        self.logger.error("Package upload failed with the following errors")
        error = {"message": ""}
        apex_test_failures = False
        for error in self.upload["Errors"]["errors"]:
            self.logger.error(f"  {error['message']}")
            if error["message"] == "ApexTestFailure":
                apex_test_failures = True

        if apex_test_failures:
            self._handle_apex_test_failures()

        exception = self._get_exception_type(error)
        raise exception("Package upload failed")

    def _handle_apex_test_failures(self):
        self.logger.error("Failed Apex Tests:")
        test_results = self._get_apex_test_results_from_upload()
        self._log_failures(test_results)

    def _get_apex_test_results_from_upload(self):
        soql_query = self._get_failed_tests_soql_query()
        return self.tooling.query(soql_query)

    def _log_failures(self, results):
        """Logs failures using CliTable"""
        table_title = "Failed Apex Tests"
        table_data = self._get_table_data(results)
        table = CliTable(table_data, table_title, wrap_cols=["Message", "Stacktrace"])
        self.logger.error(str(table))

    def _get_table_data(self, results):
        """Returns table data compatible with CliTable class"""
        table_header_row = ["Class", "Method", "Message", "Stacktrace"]
        table_data = [table_header_row]
        for test in results["records"]:
            table_data.append(
                [
                    test["ApexClass"]["Name"],
                    test["MethodName"],
                    test["Message"],
                    test["StackTrace"],
                ]
            )
        return table_data

    def _get_failed_tests_soql_query(self):
        return (
            "SELECT ApexClass.Name, "
            "MethodName, "
            "Message, "
            "StackTrace "
            "FROM ApexTestResult "
            "WHERE Outcome='Fail' "
            f"AND TestTimestamp > {self._upload_start_time.isoformat()}Z"
        )

    def _get_exception_type(self, error):
        return (
            ApexTestException
            if error["message"] == "ApexTestFailure"
            else SalesforceException
        )

    def _set_return_values(self):
        self.return_values = {
            "version_number": str(self.version_number),
            "version_id": self.version_id,
            "package_id": self.package_id,
        }

    def _log_package_upload_success(self):
        self.logger.info(
            f"Uploaded package version {self.version_number} with Id {self.version_id}"
        )

    def _set_package_version_values_on_self(self):
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
            f"PackageUploadRequest {self.upload_id} is {self.upload['Status']}"
        )

        self.poll_complete = not self._poll_again(self.upload["Status"])

    def _poll_again(self, upload_status):
        return upload_status in ["IN_PROGRESS", "QUEUED"]
