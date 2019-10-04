import pytest
from unittest import mock

from cumulusci.tasks.salesforce import PackageUpload
from cumulusci.core.exceptions import ApexTestException
from cumulusci.core.exceptions import SalesforceException
from .util import create_task


class TestPackageUpload:
    def test_run_task(self):
        task = create_task(
            PackageUpload,
            {
                "name": "Test Release",
                "description": "Description",
                "password": "pw",
                "post_install_url": "http://www.salesforce.org",
                "release_notes_url": "https://github.com",
            },
        )

        def _init_class():
            task.tooling = mock.Mock(
                query=mock.Mock(
                    side_effect=[
                        # Query for package by namespace
                        {"totalSize": 1, "records": [{"Id": "PKG_ID"}]},
                        # Query for upload status
                        {
                            "totalSize": 1,
                            "records": [
                                {
                                    "Status": "SUCCESS",
                                    "MetadataPackageVersionId": "VERSION_ID",
                                }
                            ],
                        },
                        # Query for packge version details
                        {
                            "totalSize": 1,
                            "records": [
                                {
                                    "MajorVersion": 1,
                                    "MinorVersion": 0,
                                    "PatchVersion": 1,
                                    "ReleaseState": "Beta",
                                    "BuildNumber": 1,
                                }
                            ],
                        },
                    ]
                )
            )

        task._init_class = _init_class
        task._get_tooling_object = mock.Mock(
            return_value=mock.Mock(create=mock.Mock(return_value={"id": "UPLOAD_ID"}))
        )
        task()
        assert "SUCCESS" == task.upload["Status"]

    def test_get_package_id_and_info(self):
        production = False
        name = "Test Release"
        expected_package_id = "12345"

        expected_package_info = {
            "VersionName": "Test Release",
            "IsReleaseVersion": production,
            "MetadataPackageId": expected_package_id,
        }

        task = create_task(PackageUpload, {"name": name})
        task._get_one_record = mock.Mock(return_value={"Id": "12345"})

        package_id, package_info = task._get_package_id_and_info()

        assert expected_package_id == package_id
        assert expected_package_info == package_info

    def test_set_package_info_values_from_option(self):
        password = "testPassword123"
        description = "Test Description"
        post_install_url = "https://www.post_install.com/install_now"
        release_notes_url = "https://www.release_notes.com/latest"

        options = {
            "name": "test_name",
            "description": description,
            "password": password,
            "post_install_url": post_install_url,
            "release_notes_url": release_notes_url,
        }
        task = create_task(PackageUpload, options)

        package_info = {}
        task._set_package_info_values_from_options(package_info)

        assert len(package_info.keys()) == 4
        assert package_info["Description"] == description
        assert package_info["Password"] == password
        assert package_info["PostInstallUrl"] == post_install_url
        assert package_info["ReleaseNotesUrl"] == release_notes_url

    @mock.patch("cumulusci.tasks.salesforce.package_upload.time")
    def test_make_package_upload_request(self, time):
        task = create_task(PackageUpload, {"name": "Test Release"})

        upload_id = "asdf12345"
        package_upload_request = mock.Mock(
            create=mock.Mock(return_value={"id": upload_id})
        )

        task._poll = mock.Mock()
        task.logger = mock.Mock(info=mock.Mock())
        task._get_tooling_object = mock.Mock(return_value=package_upload_request)

        package_info = {}
        package_id = "12345asdf"
        time.time = mock.Mock(return_value=10)
        task._make_package_upload_request(package_info, package_id)

        assert task._upload_start_time == 10
        assert task.logger.info.called_once_with(
            f"Created PackageUploadRequest {upload_id} for Package {package_id}"
        )

    def test_log_package_upload_errors(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        task.logger = mock.Mock(error=mock.Mock())
        task._log_apex_test_failures = mock.Mock()

        task.upload = {
            "Errors": {
                "errors": [{"message": "DmlException"}, {"message": "DmlException"}]
            }
        }
        with pytest.raises(SalesforceException):
            task._log_package_upload_errors()

        assert task.logger.error.call_count == 3
        assert not task._log_apex_test_failures.called

    def test_get_exception_type(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        apex_test_error = {"message": "ApexTestFailure"}
        assert task._get_exception_type(apex_test_error) == ApexTestException

        other_salesforce_error = {"message": "DmlException"}
        assert task._get_exception_type(other_salesforce_error) == SalesforceException

    def test_log_apex_test_failures(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        task.logger = mock.Mock(error=mock.Mock())
        task._get_failed_tests_soql_query = mock.Mock(return_value="")
        task.tooling = mock.Mock(
            query=mock.Mock(
                return_value={
                    "records": [
                        {
                            "ApexClass": {"Name": "Class1"},
                            "MethodName": "method1",
                            "StackTrace": "stacktrace1",
                        },
                        {
                            "ApexClass": {"Name": "Class2"},
                            "MethodName": "method2",
                            "StackTrace": "stacktrace2",
                        },
                    ]
                }
            )
        )

        task._log_apex_test_failures()

        # CliTable.echo() doesn't utilize logger
        task.logger.error.assert_called_once()

    def test_get_failed_tests_soql_qeury(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        iso_datetime = "1970-01-01T00:00:00.000"
        task._get_package_upload_iso_timestamp = mock.Mock(return_value=iso_datetime)

        returned_query = task._get_failed_tests_soql_query()

        assert returned_query.endswith(f"TestTimestamp > {iso_datetime}Z")

    def test_run_task__upload_error(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        def _init_class():
            task._log_apex_test_failures = mock.Mock()
            task.tooling = mock.Mock(
                query=mock.Mock(
                    side_effect=[
                        # Query for package by namespace
                        {"totalSize": 1, "records": [{"Id": "PKG_ID"}]},
                        # Query for upload status
                        {
                            "totalSize": 1,
                            "records": [
                                {
                                    "Status": "ERROR",
                                    "Errors": {
                                        "errors": [{"message": "ApexTestFailure"}]
                                    },
                                }
                            ],
                        },
                    ]
                )
            )

        task._init_class = _init_class
        task._get_tooling_object = mock.Mock(
            return_value=mock.Mock(create=mock.Mock(return_value={"id": "UPLOAD_ID"}))
        )
        with pytest.raises(ApexTestException):
            task()
        assert "ERROR" == task.upload["Status"]

    def test_get_one__no_result(self):
        task = create_task(PackageUpload, {"name": "Test Release"})
        task.tooling = mock.Mock(query=mock.Mock(return_value={"totalSize": 0}))
        with pytest.raises(SalesforceException):
            task._get_one_record(None, None)

    def test_set_return_values(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        version_number = "1.2.3"
        version_id = "version_id"

        task.version_id = version_id
        task.version_number = version_number

        package_id = "package_id"
        task._set_return_values(package_id)

        assert task.return_values is not None
        assert task.return_values["package_id"] == package_id
        assert task.return_values["version_id"] == version_id
        assert task.return_values["version_number"] == version_number

    def test_log_package_upload_success(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        task.logger = mock.Mock(info=mock.Mock())

        version_id = "version_id"
        version_number = "version_number"

        task.version_id = version_id
        task.version_number = version_number

        task._log_package_upload_success()

        assert task.logger.info.called_once_with(
            f"Uploaded package version {version_number} with Id {version_id}"
        )

    def test_set_package_version_values_on_self(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        version_id = "version_id"
        major_version = 1
        minor_version = 2
        patch_version = 3
        build_number = 4

        task.upload = {"MetadataPackageVersionId": version_id}
        task._get_one_record = mock.Mock(
            return_value={
                "MajorVersion": major_version,
                "MinorVersion": minor_version,
                "PatchVersion": patch_version,
                "ReleaseState": "Beta",
                "BuildNumber": build_number,
            }
        )

        task._set_package_version_values_on_self()

        assert task.version_id == version_id
        assert (
            f"{major_version}.{minor_version}.{patch_version} (Beta {build_number})"
            == task.version_number
        )
