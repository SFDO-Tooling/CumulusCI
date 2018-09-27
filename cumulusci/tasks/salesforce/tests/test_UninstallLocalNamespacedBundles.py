import mock
import unittest

from cumulusci.tasks.salesforce import UninstallLocalNamespacedBundles
from cumulusci.tests.util import create_project_config
from cumulusci.utils import temporary_dir
from .util import create_task


class TestUninstallLocalNamespacedBundles(unittest.TestCase):
    @mock.patch("cumulusci.tasks.metadata.package.PackageXmlGenerator.__call__")
    def test_get_destructive_changes(self, PackageXmlGenerator):
        with temporary_dir() as path:
            project_config = create_project_config()
            project_config.config["project"]["package"]["namespace"] = "ns"
            task = create_task(
                UninstallLocalNamespacedBundles,
                {"path": path, "managed": True, "filename_token": "%TOKEN%"},
                project_config,
            )
            PackageXmlGenerator.return_value = "%TOKEN%"
            self.assertEqual("ns__", task._get_destructive_changes())
