from unittest import mock

from cumulusci.tasks.salesforce import UninstallLocal
from cumulusci.utils import temporary_dir

from .util import create_task


class TestUninstallLocal:
    @mock.patch("cumulusci.tasks.metadata.package.PackageXmlGenerator.__call__")
    def test_get_destructive_changes(self, PackageXmlGenerator):
        with temporary_dir() as path:
            task = create_task(UninstallLocal, {"path": path})
            PackageXmlGenerator.return_value = mock.sentinel.package_xml
            assert mock.sentinel.package_xml == task._get_destructive_changes()
