from cumulusci.core.processors import CallablePackageZipBuilder
from xml.sax.saxutils import escape

INSTALLED_PACKAGE_PACKAGE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>{namespace}</members>
    <name>InstalledPackage</name>
  </types>
<version>{version}</version>
</Package>"""

EMPTY_PACKAGE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
<version>{version}</version>
</Package>"""

FULL_NAME_PACKAGE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
<fullName>{}</fullName>
<version>{}</version>
</Package>"""

INSTALLED_PACKAGE = """<?xml version="1.0" encoding="UTF-8"?>
<InstalledPackage xmlns="http://soap.sforce.com/2006/04/metadata">
  <versionNumber>{}</versionNumber>
  <activateRSS>false</activateRSS>
</InstalledPackage>"""


class ZipfilePackageZipBuilder(CallablePackageZipBuilder):
    def __init__(self, zipfile):
        self.zip = zipfile
        self._stream = zipfile.fp

    def _open_zip(self):
        pass

    def _populate_zip(self):
        pass

class CreatePackageZipBuilder(CallablePackageZipBuilder):

    def __init__(self, name, api_version):
        if not name:
            raise ValueError('You must provide a name to create a package')
        if not api_version:
            raise ValueError('You must provide an api_version to create a package')
        self.name= name
        self.api_version= api_version

    def _populate_zip(self):
        package_xml = FULL_NAME_PACKAGE_XML.format(escape(self.name), self.api_version)
        self._write_package_xml(package_xml)

class InstallPackageZipBuilder(CallablePackageZipBuilder):
    api_version = '43.0'

    def __init__(self, namespace, version):
        if not namespace:
            raise ValueError('You must provide a namespace to install a package')
        if not version:
            raise ValueError('You must provide a version to install a package')
        self.namespace = namespace
        self.version = version

    def _populate_zip(self):
        package_xml = INSTALLED_PACKAGE_PACKAGE_XML.format(
            namespace=self.namespace,
            version=self.api_version,
        )
        self._write_package_xml(package_xml)

        installed_package = INSTALLED_PACKAGE.format(self.version)
        self._write_file(
            'installedPackages/{}.installedPackage'.format(self.namespace),
            installed_package
        )

class DestructiveChangesZipBuilder(CallablePackageZipBuilder):

    def __init__(self, destructive_changes, version):
        self.destructive_changes = destructive_changes
        self.version = version

    def _populate_zip(self): 
        self._write_package_xml(EMPTY_PACKAGE_XML.format(version=self.version))
        self._write_file('destructiveChanges.xml', self.destructive_changes)

class UninstallPackageZipBuilder(DestructiveChangesZipBuilder):

    def __init__(self, namespace, version):
        if not namespace:
            raise ValueError('You must provide a namespace to install a package')
        self.namespace = namespace
        self.version = version
        self.destructive_changes = INSTALLED_PACKAGE_PACKAGE_XML.format(
            namespace=self.namespace,
            version=self.version,
        )
