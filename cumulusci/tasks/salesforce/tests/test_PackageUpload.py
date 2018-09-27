import mock
import unittest

from cumulusci.tasks.salesforce import PackageUpload
from cumulusci.core.exceptions import ApexTestException
from cumulusci.core.exceptions import SalesforceException
from .util import create_task


class TestPackageUpload(unittest.TestCase):
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
        task.tooling.query = mock.Mock(
            side_effect=[
                # Query for package by namespace
                {"totalSize": 1, "records": [{"Id": "PKG_ID"}]},
                # Query for upload status
                {
                    "totalSize": 1,
                    "records": [
                        {"Status": "SUCCESS", "MetadataPackageVersionId": "VERSION_ID"}
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
        task._get_tooling_object = mock.Mock(
            return_value=mock.Mock(create=mock.Mock(return_value={"id": "UPLOAD_ID"}))
        )
        task()
        self.assertEqual("SUCCESS", task.upload["Status"])

    def test_run_task__upload_error(self):
        task = create_task(PackageUpload, {"name": "Test Release"})
        task.tooling.query = mock.Mock(
            side_effect=[
                # Query for package by namespace
                {"totalSize": 1, "records": [{"Id": "PKG_ID"}]},
                # Query for upload status
                {
                    "totalSize": 1,
                    "records": [
                        {
                            "Status": "ERROR",
                            "Errors": {"errors": [{"message": "ApexTestFailure"}]},
                        }
                    ],
                },
            ]
        )
        task._get_tooling_object = mock.Mock(
            return_value=mock.Mock(create=mock.Mock(return_value={"id": "UPLOAD_ID"}))
        )
        with self.assertRaises(ApexTestException):
            task()
        self.assertEqual("ERROR", task.upload["Status"])

    def test_get_one__no_result(self):
        task = create_task(PackageUpload, {"name": "Test Release"})
        task.tooling.query = mock.Mock(return_value={"totalSize": 0})
        with self.assertRaises(SalesforceException):
            task._get_one(None, None)
