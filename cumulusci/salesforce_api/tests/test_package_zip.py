import mock
import unittest

from cumulusci.salesforce_api.package_zip import BasePackageZipBuilder
from cumulusci.salesforce_api.package_zip import ZipfilePackageZipBuilder
from cumulusci.salesforce_api.package_zip import CreatePackageZipBuilder
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.salesforce_api.package_zip import DestructiveChangesZipBuilder
from cumulusci.salesforce_api.package_zip import UninstallPackageZipBuilder


class TestBasePackageZipBuilder(unittest.TestCase):
    def test_populate_zip(self):
        builder = BasePackageZipBuilder()
        with self.assertRaises(NotImplementedError):
            builder._populate_zip()


class TestZipfilePackageZipBuilder(unittest.TestCase):
    def test_init(self):
        zf = mock.Mock()
        builder = ZipfilePackageZipBuilder(zf)
        self.assertIs(zf, builder.zip)

    def test_open_zip(self):
        zf = mock.Mock()
        builder = ZipfilePackageZipBuilder(zf)
        builder._open_zip()

    def test_populate_zip(self):
        zf = mock.Mock()
        builder = ZipfilePackageZipBuilder(zf)
        builder._populate_zip()


class TestCreatePackageZipBuilder(unittest.TestCase):
    def test_init__missing_name(self):
        with self.assertRaises(ValueError):
            builder = CreatePackageZipBuilder(None, "43.0")

    def test_init__missing_api_version(self):
        with self.assertRaises(ValueError):
            builder = CreatePackageZipBuilder("TestPackage", None)


class TestInstallPackageZipBuilder(unittest.TestCase):
    def test_init__missing_namespace(self):
        with self.assertRaises(ValueError):
            builder = InstallPackageZipBuilder(None, "1.0")

    def test_init__missing_version(self):
        with self.assertRaises(ValueError):
            builder = InstallPackageZipBuilder("testns", None)


class TestDestructiveChangesZipBuilder(unittest.TestCase):
    def test_call(self):
        builder = DestructiveChangesZipBuilder("", "1.0")
        builder()
        names = builder.zip.namelist()
        self.assertIn("package.xml", names)
        self.assertIn("destructiveChanges.xml", names)


class TestUninstallPackageZipBuilder(unittest.TestCase):
    def test_init__missing_namespace(self):
        with self.assertRaises(ValueError):
            builder = UninstallPackageZipBuilder(None, "1.0")

    def test_call(self):
        builder = UninstallPackageZipBuilder("testns", "1.0")
        builder()
        self.assertIn("destructiveChanges.xml", builder.zip.namelist())
