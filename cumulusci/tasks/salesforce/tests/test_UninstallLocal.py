from unittest import mock
import unittest

from cumulusci.tasks.salesforce import UninstallLocal
from cumulusci.utils import temporary_dir
from .util import create_task


class TestUninstallLocal(unittest.TestCase):
    @mock.patch("cumulusci.tasks.metadata.package.PackageXmlGenerator.__call__")
    def test_get_destructive_changes(self, PackageXmlGenerator):
        with temporary_dir() as path:
            task = create_task(UninstallLocal, {"path": path})
            PackageXmlGenerator.return_value = mock.sentinel.package_xml
            self.assertEqual(mock.sentinel.package_xml, task._get_destructive_changes())
