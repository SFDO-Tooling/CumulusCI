from collections import defaultdict
from unittest import mock

import pytest

from cumulusci.core.config.org_config import OrgConfig, VersionInfo
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.config.universal_config import UniversalConfig
from cumulusci.core.exceptions import (
    ApexTestException,
    SalesforceException,
    TaskOptionsError,
)
from cumulusci.tasks.salesforce import PackageUpload

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
                "major_version": "2",
                "minor_version": "11",
            },
        )

        def _init_class():
            task.tooling = mock.Mock(
                query=mock.Mock(
                    side_effect=[
                        # Query for latest major and minor version used via validate version function
                        {
                            "totalSize": 1,
                            "records": [
                                {
                                    "MajorVersion": 1,
                                    "MinorVersion": 0,
                                    "PatchVersion": 1,
                                    "ReleaseState": "Released",
                                }
                            ],
                        },
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
        assert task.upload["Status"] == "SUCCESS"

    def test_set_package_id(self):
        name = "Test Release"
        expected_package_id = "1234567890"

        task = create_task(PackageUpload, {"name": name})
        task._get_one_record = mock.Mock(return_value={"Id": expected_package_id})

        task._set_package_id()
        assert expected_package_id == task.package_id

    test_validate_version_base_options = {
        "name": "Test Release",
        "production": False,
        "description": "Test Description",
        "password": "secret",
        "post_install_url": "post.install.url",
        "release_notes_url": "release.notes.url",
    }

    def generate_valid_version_options(
        major_version: str,
        minor_version: str,
        asserted_major_version: str,
        asserted_minor_version: str,
        is_negative: bool = False,
    ):

        """This is function is used to generate test cases for test_validate_versions(positive as well as negative)
        Arguments:
            major_version:acutal major version which is to be passed none if not passed.
            minor_version:acutal minor version which is to be passed none if not passed
            asserted_major_version:major version which is expected in options dict after running of validate version function.
            asserted_minor_version:minor version which is expected in options dict after running of validate version function.
            is_negative:This boolean is used to decide whether the function returns a postive or negative test case. defaults to true is not passed.
        """
        test_validate_version_base_options = {
            "name": "Test Release",
            "production": False,
            "description": "Test Description",
            "password": "secret",
            "post_install_url": "post.install.url",
            "release_notes_url": "release.notes.url",
        }
        test_case_actual = {
            **test_validate_version_base_options,
        }
        if major_version is not None:
            test_case_actual["major_version"] = major_version
        if minor_version is not None:
            test_case_actual["minor_version"] = minor_version

        test_case_expected = {
            **test_validate_version_base_options,
            "major_version": str(asserted_major_version),
            "minor_version": str(asserted_minor_version),
        }

        if is_negative:
            return test_case_actual
        return test_case_actual, test_case_expected

    # Generating Positive Test Cases for test_validate_versions
    test_positive_options = [
        generate_valid_version_options("1", "2", "1", "2"),
        generate_valid_version_options("2", "1", "2", "1"),
        generate_valid_version_options(None, "2", "1", "2"),
        generate_valid_version_options("1", None, "1", "2"),
        generate_valid_version_options("2", None, "2", "0"),
        generate_valid_version_options(None, None, "1", "2"),
    ]

    @pytest.mark.parametrize("actual_options,expected_options", test_positive_options)
    def test_positive_validate_versions(self, actual_options, expected_options):
        """Runs Postive Tests for tests_validate_versions"""
        task = create_task(PackageUpload, actual_options)
        task._get_one_record = mock.Mock(
            return_value={
                "MajorVersion": 1,
                "MinorVersion": 1,
                "PatchVersion": 0,
                "ReleaseState": "Released",
            }
        )
        task._validate_versions()

        assert task.options["name"] == expected_options["name"]
        assert task.options["production"] == expected_options["production"]
        assert task.options["password"] == expected_options["password"]
        assert task.options["post_install_url"] == expected_options["post_install_url"]
        assert (
            task.options["release_notes_url"] == expected_options["release_notes_url"]
        )
        assert task.options["major_version"] == expected_options["major_version"]
        assert task.options["minor_version"] == expected_options["minor_version"]

    test_positive_options_beta = [
        generate_valid_version_options("1", None, "1", "1"),
        generate_valid_version_options("1", "1", "1", "1"),
        generate_valid_version_options(None, "1", "1", "1"),
        generate_valid_version_options(None, None, "1", "1"),
    ]

    @pytest.mark.parametrize(
        "actual_options,expected_options", test_positive_options_beta
    )
    def test_positive_validate_versions_for_beta(
        self, actual_options, expected_options
    ):

        task = create_task(PackageUpload, actual_options)
        task._get_one_record = mock.Mock(
            return_value={
                "MajorVersion": 1,
                "MinorVersion": 1,
                "PatchVersion": 0,
                "ReleaseState": "Beta",
            }
        )
        task._validate_versions()

        assert task.options["name"] == expected_options["name"]
        assert task.options["production"] == expected_options["production"]
        assert task.options["password"] == expected_options["password"]
        assert task.options["post_install_url"] == expected_options["post_install_url"]
        assert (
            task.options["release_notes_url"] == expected_options["release_notes_url"]
        )
        assert task.options["major_version"] == expected_options["major_version"]
        assert task.options["minor_version"] == expected_options["minor_version"]

    # Generating Negative Test Cases for test_validate_versions
    test_negative_options = [
        generate_valid_version_options("0", "2", None, None, True),
        generate_valid_version_options("1", "0", None, None, True),
        generate_valid_version_options(None, "1", None, None, True),
        generate_valid_version_options("ab", 0, None, None, True),
        generate_valid_version_options("1", "ab", None, None, True),
    ]

    @pytest.mark.parametrize("actual_options", test_negative_options)
    def test_negative_validate_versions(self, actual_options):
        """Running Negative Tests for tests_validate_versions"""
        task = create_task(PackageUpload, actual_options)
        task._get_one_record = mock.Mock(
            return_value={
                "MajorVersion": 1,
                "MinorVersion": 1,
                "PatchVersion": 0,
                "ReleaseState": "Released",
            }
        )
        with pytest.raises(TaskOptionsError):
            task._validate_versions()

    test_negative_options_beta = [
        generate_valid_version_options("1", "2", None, None, True),
        generate_valid_version_options(None, "2", None, None, True),
    ]

    @pytest.mark.parametrize("actual_options", test_negative_options_beta)
    def test_negative_validate_versions_beta(self, actual_options):
        """Running Negative Tests for tests_validate_versions"""
        task = create_task(PackageUpload, actual_options)
        task._get_one_record = mock.Mock(
            return_value={
                "MajorVersion": 1,
                "MinorVersion": 1,
                "PatchVersion": 0,
                "ReleaseState": "Beta",
            }
        )
        with pytest.raises(TaskOptionsError):
            task._validate_versions()

    def test_set_package_info(self):
        expected_package_id = "12345"
        options = {
            "name": "Test Release",
            "production": False,
            "description": "Test Description",
            "password": "secret",
            "post_install_url": "post.install.url",
            "release_notes_url": "release.notes.url",
            "major_version": "2",
            "minor_version": "2",
        }

        task = create_task(PackageUpload, options)
        task._get_one_record = mock.Mock(return_value={"Id": expected_package_id})

        with pytest.raises(AttributeError):
            task.package_info

        task._set_package_info()

        assert options["name"] == task.package_info["VersionName"]
        assert options["production"] == task.package_info["IsReleaseVersion"]
        assert expected_package_id == task.package_info["MetadataPackageId"]
        assert options["description"] == task.package_info["Description"]
        assert options["password"] == task.package_info["Password"]
        assert options["post_install_url"] == task.package_info["PostInstallUrl"]
        assert options["release_notes_url"] == task.package_info["ReleaseNotesUrl"]
        assert options["major_version"] == task.package_info["MajorVersion"]
        assert options["minor_version"] == task.package_info["MinorVersion"]

    @mock.patch("cumulusci.tasks.salesforce.package_upload.datetime")
    def test_make_package_upload_request(self, datetime):
        upload_start_time = "1970-01-01T00:00:00.0000Z"
        datetime.utcnow = mock.Mock(return_value=upload_start_time)

        upload_id = "asdf12345"
        package_upload_request = mock.Mock(
            create=mock.Mock(return_value={"id": upload_id})
        )

        package_id = "1234567890"
        task = create_task(PackageUpload, {"name": "Test Release"})
        task._poll = mock.Mock()
        task.package_info = {}
        task.package_id = package_id
        task.logger = mock.Mock(info=mock.Mock())
        task._get_tooling_object = mock.Mock(return_value=package_upload_request)

        task._make_package_upload_request()

        assert task._upload_start_time == upload_start_time
        task.logger.info.assert_called_once_with(
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

    def test_handle_apex_test_failures(self):
        task = create_task(PackageUpload, {"name": "Test Release"})
        task.logger = mock.Mock(error=mock.Mock())
        task._get_apex_test_results_from_upload = mock.Mock()
        task._log_failures = mock.Mock()

        task._handle_apex_test_failures()

        task.logger.error.assert_called_once_with("Failed Apex Tests:")
        assert task._get_apex_test_results_from_upload.call_count == 1
        assert task._log_failures.call_count == 1

    @mock.patch("cumulusci.tasks.salesforce.package_upload.CliTable", autospec=True)
    def test_log_failures(self, table):

        task = create_task(PackageUpload, {"name": "Test Release"})

        table_data = [1, 2, 3, 4]
        task._get_table_data = mock.Mock(return_value=table_data)

        results = "Test Results"
        task._log_failures(results)

        table.assert_called_once_with(
            table_data,
            "Failed Apex Tests",
        )
        table.return_value.echo.assert_called()

    def test_get_table_data(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        results = {
            "records": [
                {
                    "ApexClass": {"Name": "Class1"},
                    "MethodName": "Method1",
                    "Message": "Message1",
                    "StackTrace": "StackTrace1",
                },
                {
                    "ApexClass": {"Name": "Class2"},
                    "MethodName": "Method2",
                    "Message": "Message2",
                    "StackTrace": "StackTrace2",
                },
                {
                    "ApexClass": {"Name": "Class3"},
                    "MethodName": "Method3",
                    "Message": "Message3",
                    "StackTrace": "StackTrace3",
                },
            ]
        }

        table_data = task._get_table_data(results)

        expected_table_data = [
            ["Class", "Method", "Message", "Stacktrace"],
            ["Class1", "Method1", "Message1", "StackTrace1"],
            ["Class2", "Method2", "Message2", "StackTrace2"],
            ["Class3", "Method3", "Message3", "StackTrace3"],
        ]
        assert expected_table_data == table_data

    def test_get_failed_tests_soql_qeury(self):
        task = create_task(PackageUpload, {"name": "Test Release"})
        iso_datetime = "1970-01-01T00:00:00.000"
        task._upload_start_time = mock.Mock(
            isoformat=mock.Mock(return_value=iso_datetime)
        )

        returned_query = task._get_failed_tests_soql_query()

        assert returned_query.endswith(f"TestTimestamp > {iso_datetime}Z")

    def test_run_task__upload_error(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        def _init_class():
            task._handle_apex_test_failures = mock.Mock()
            task.tooling = mock.Mock(
                query=mock.Mock(
                    side_effect=[
                        # Query for latest major and minor version
                        {
                            "totalSize": 1,
                            "records": [
                                {
                                    "MajorVersion": 1,
                                    "MinorVersion": 0,
                                    "PatchVersion": 1,
                                    "ReleaseState": "Released",
                                }
                            ],
                        },
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
        assert task.upload["Status"] == "ERROR"

    def test_get_one__no_result(self):
        task = create_task(PackageUpload, {"name": "Test Release"})
        task.tooling = mock.Mock(query=mock.Mock(return_value={"totalSize": 0}))
        with pytest.raises(SalesforceException):
            task._get_one_record(None, None)

    def test_set_return_values(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        task.package_id = "package_id"
        task.version_id = "003000000000000"
        task.version_number = "1.2.3"

        task._set_return_values()

        assert task.return_values is not None
        assert task.return_values["package_id"] == task.package_id
        assert task.return_values["version_id"] == task.version_id
        assert task.return_values["version_number"] == task.version_number

    def test_set_dependencies(self):
        project_config = BaseProjectConfig(UniversalConfig())
        project_config.project__dependencies = [{"namespace": "foo", "version": "1.0"}]
        org_config = OrgConfig({}, "test")
        org_config._installed_packages = defaultdict(list)
        org_config._installed_packages["foo@1.0"] = [
            VersionInfo("04t000000000000", "1.0")
        ]

        task = create_task(
            PackageUpload,
            {"name": "Test Release"},
            project_config=project_config,
            org_config=org_config,
        )

        task._set_dependencies()

        assert task.return_values["dependencies"] == [{"version_id": "04t000000000000"}]

    def test_log_package_upload_success(self):
        task = create_task(PackageUpload, {"name": "Test Release"})

        task.logger = mock.Mock(info=mock.Mock())

        version_id = "version_id"
        version_number = "version_number"

        task.version_id = version_id
        task.version_number = version_number

        task._log_package_upload_success()

        task.logger.info.assert_called_once_with(
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
