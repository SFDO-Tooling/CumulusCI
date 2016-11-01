from base64 import b64encode
from zipfile import ZipFile
from tempfile import TemporaryFile

INSTALLED_PACKAGE_PACKAGE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
  <types>
    <members>{}</members>
    <name>InstalledPackage</name>
  </types>
<version>33.0</version>
</Package>"""

EMPTY_PACKAGE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
<version>33.0</version>
</Package>"""

FULL_NAME_PACKAGE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
<fullName>{}</fullName>
<version>{}</version>
</Package>"""

INSTALLED_PACKAGE = """<?xml version="1.0" encoding="UTF-8"?>
<InstalledPackage xmlns="http://soap.sforce.com/2006/04/metadata">
  <versionNumber>{}</versionNumber>
</InstalledPackage>"""

class BasePackageZipBuilder(object):

    def __call__(self):
        self._open_zip()
        self._populate_zip()
        return self._encode_zip()

    def _open_zip(self):
        self.zip_file = TemporaryFile()
        self.zip= ZipFile(self.zip_file, 'w')

    def _populate_zip(self):
        raise NotImplementedError('Subclasses need to provide their own implementation')

    def _write_package_xml(self, package_xml):
        self.zip.writestr('package.xml', package_xml)

    def _write_file(self, path, content):
        self.zip.writestr(path, content)

    def _encode_zip(self):
        self.zip.close()
        self.zip_file.seek(0)
        return b64encode(self.zip_file.read())

class CreatePackageZipBuilder(BasePackageZipBuilder):

    def __init__(self, name, api_version):
        if not name:
            raise ValueError('You must provide a name to create a package')
        if not api_version:
            raise ValueError('You must provide an api_version to create a package')
        self.name= name
        self.api_version= api_version

    def _populate_zip(self):
        package_xml = FULL_NAME_PACKAGE_XML.format(self.name, self.api_version)
        self._write_package_xml(package_xml)

class InstallPackageZipBuilder(BasePackageZipBuilder):

    def __init__(self, namespace, version):
        if not namespace:
            raise ValueError('You must provide a namespace to install a package')
        if not version:
            raise ValueError('You must provide a version to install a package')
        self.namespace = namespace
        self.version = version

    def _populate_zip(self):
        package_xml = INSTALLED_PACKAGE_PACKAGE_XML.format(self.namespace)
        self._write_package_xml(package_xml)

        installed_package = INSTALLED_PACKAGE.format(self.version)
        self._write_file(
            'installedPackages/{}.installedPackage'.format(self.namespace),
            installed_package
        )

class DestructiveChangesZipBuilder(BasePackageZipBuilder):

    def __init__(self, destructive_changes):
        self.destructive_changes = destructive_changes

    def _populate_zip(self): 
        self._write_package_xml(EMPTY_PACKAGE_XML)
        self._write_file('destructiveChanges.xml', self.destructive_changes)

class UninstallPackageZipBuilder(DestructiveChangesZipBuilder):

    def __init__(self, namespace):
        if not namespace:
            raise ValueError('You must provide a namespace to install a package')
        self.namespace = namespace
        self.destructive_changes = INSTALLED_PACKAGE_PACKAGE_XML.format(self.namespace)
