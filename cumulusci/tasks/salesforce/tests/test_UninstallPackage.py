import mock
import unittest

from cumulusci.tasks.salesforce import UninstallPackage
from cumulusci.tests.util import create_project_config
from .util import create_task


class TestUninstallPackage(unittest.TestCase):
    @mock.patch(
        "cumulusci.salesforce_api.package_zip.UninstallPackageZipBuilder.__call__"
    )
    def test_get_destructive_changes(self, UninstallPackageZipBuilder):
        project_config = create_project_config()
        project_config.config["project"]["package"]["namespace"] = "ns"
        task = create_task(UninstallPackage, {}, project_config)
        task.api_class = mock.Mock()
        task._get_api()
        UninstallPackageZipBuilder.assert_called_once()
