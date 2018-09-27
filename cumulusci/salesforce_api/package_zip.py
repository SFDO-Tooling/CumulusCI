from base64 import b64encode
from zipfile import ZipFile
from tempfile import TemporaryFile
from xml.sax.saxutils import escape

INSTALLED_PACKAGE_PACKAGE_XML = u"""<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>{namespace}</members>
    <name>InstalledPackage</name>
  </types>
<version>{version}</version>
</Package>"""

EMPTY_PACKAGE_XML = u"""<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
<version>{version}</version>
</Package>"""

FULL_NAME_PACKAGE_XML = u"""<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
<fullName>{}</fullName>
<version>{}</version>
</Package>"""

INSTALLED_PACKAGE = u"""<?xml version="1.0" encoding="UTF-8"?>
<InstalledPackage xmlns="http://soap.sforce.com/2006/04/metadata">
  <versionNumber>{}</versionNumber>
  <activateRSS>false</activateRSS>
</InstalledPackage>"""


class BasePackageZipBuilder(object):
    def __call__(self):
        self._open_zip()
        self._populate_zip()
        return self._encode_zip()

    def _open_zip(self):
        self.zip_file = TemporaryFile()
        self.zip = ZipFile(self.zip_file, "w")

    def _populate_zip(self):
        raise NotImplementedError("Subclasses need to provide their own implementation")

    def _write_package_xml(self, package_xml):
        self.zip.writestr("package.xml", package_xml)

    def _write_file(self, path, content):
        self.zip.writestr(path, content)

    def _encode_zip(self):
        self.zip.close()
        self.zip_file.seek(0)
        return b64encode(self.zip_file.read()).decode("utf-8")


class ZipfilePackageZipBuilder(BasePackageZipBuilder):
    def __init__(self, zipfile):
        self.zip = zipfile
        self.zip_file = zipfile.fp

    def _open_zip(self):
        pass

    def _populate_zip(self):
        pass


class CreatePackageZipBuilder(BasePackageZipBuilder):
    def __init__(self, name, api_version):
        if not name:
            raise ValueError("You must provide a name to create a package")
        if not api_version:
            raise ValueError("You must provide an api_version to create a package")
        self.name = name
        self.api_version = api_version

    def _populate_zip(self):
        package_xml = FULL_NAME_PACKAGE_XML.format(escape(self.name), self.api_version)
        self._write_package_xml(package_xml)


class InstallPackageZipBuilder(BasePackageZipBuilder):
    api_version = "43.0"

    def __init__(self, namespace, version):
        if not namespace:
            raise ValueError("You must provide a namespace to install a package")
        if not version:
            raise ValueError("You must provide a version to install a package")
        self.namespace = namespace
        self.version = version

    def _populate_zip(self):
        package_xml = INSTALLED_PACKAGE_PACKAGE_XML.format(
            namespace=self.namespace, version=self.api_version
        )
        self._write_package_xml(package_xml)

        installed_package = INSTALLED_PACKAGE.format(self.version)
        self._write_file(
            "installedPackages/{}.installedPackage".format(self.namespace),
            installed_package,
        )


class DestructiveChangesZipBuilder(BasePackageZipBuilder):
    def __init__(self, destructive_changes, version):
        self.destructive_changes = destructive_changes
        self.version = version

    def _populate_zip(self):
        self._write_package_xml(EMPTY_PACKAGE_XML.format(version=self.version))
        self._write_file("destructiveChanges.xml", self.destructive_changes)


class UninstallPackageZipBuilder(DestructiveChangesZipBuilder):
    def __init__(self, namespace, version):
        if not namespace:
            raise ValueError("You must provide a namespace to install a package")
        self.namespace = namespace
        self.version = version
        self.destructive_changes = INSTALLED_PACKAGE_PACKAGE_XML.format(
            namespace=self.namespace, version=self.version
        )
