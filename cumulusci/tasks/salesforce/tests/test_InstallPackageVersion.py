import base64
import io
from unittest import mock
import unittest
import zipfile

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.tasks.salesforce import InstallPackageVersion
from cumulusci.tests.util import create_project_config
from .util import create_task


class TestInstallPackageVersion(unittest.TestCase):
    def test_run_task_with_retry(self):
        project_config = create_project_config()
        project_config.get_latest_version = mock.Mock(return_value="1.0")
        project_config.config["project"]["package"]["namespace"] = "ns"
        task = create_task(InstallPackageVersion, {"version": "latest"}, project_config)
        not_yet = MetadataApiError("This package is not yet available", None)
        api = mock.Mock(side_effect=[not_yet, None])
        task.api_class = mock.Mock(return_value=api)
        task()
        self.assertEqual(2, api.call_count)

    def test_run_task__options(self):
        project_config = create_project_config()
        project_config.get_latest_version = mock.Mock(return_value="1.0 (Beta 1)")
        project_config.config["project"]["package"]["namespace"] = "ns"
        task = create_task(
            InstallPackageVersion,
            {
                "version": "latest_beta",
                "activateRSS": True,
                "password": "astro",
                "security_type": "NONE",
            },
            project_config,
        )
        api = task._get_api()
        zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
        package_xml = zf.read("installedPackages/ns.installedPackage")
        self.assertIn(b"<activateRSS>true</activateRSS", package_xml)
        self.assertIn(b"<password>astro</password>", package_xml)
        self.assertIn(b"<securityType>NONE</securityType>", package_xml)

    def test_run_task__bad_security_type(self):
        project_config = create_project_config()
        project_config.get_latest_version = mock.Mock(return_value="1.0")
        project_config.config["project"]["package"]["namespace"] = "ns"
        with self.assertRaises(TaskOptionsError):
            create_task(
                InstallPackageVersion,
                {"version": "latest", "security_type": "BOGUS"},
                project_config,
            )
