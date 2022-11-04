import html
import io
import logging
import os
import pathlib
import typing as T
import zipfile
from base64 import b64encode
from xml.sax.saxutils import escape

from cumulusci.core.source_transforms.transforms import (
    BundleStaticResourcesOptions,
    BundleStaticResourcesTransform,
    CleanMetaXMLTransform,
    NamespaceInjectionOptions,
    NamespaceInjectionTransform,
    RemoveFeatureParametersTransform,
    SourceTransform,
)
from cumulusci.utils.ziputils import hash_zipfile_contents

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
  <activateRSS>{}</activateRSS>
  <securityType>{}</securityType>
  {}
</InstalledPackage>"""

DEFAULT_LOGGER = logging.getLogger(__name__)


class BasePackageZipBuilder(object):
    def __init__(self):
        self._open_zip()

    def _open_zip(self):
        """Start a new, empty zipfile"""
        self.buffer = io.BytesIO()
        self.zf = zipfile.ZipFile(self.buffer, "w", zipfile.ZIP_DEFLATED)

    def _write_package_xml(self, package_xml):
        self.zf.writestr("package.xml", package_xml)

    def _write_file(self, path, content):
        self.zf.writestr(path, content)

    def as_bytes(self) -> bytes:
        fp = self.zf.fp
        self.zf.close()
        value = fp.getvalue()
        fp.close()
        return value

    def as_base64(self) -> str:
        return b64encode(self.as_bytes()).decode("utf-8")

    def as_hash(self) -> str:
        return hash_zipfile_contents(self.zf)

    def __call__(self) -> str:
        # for backwards compatibility
        return self.as_base64()


class MetadataPackageZipBuilder(BasePackageZipBuilder):
    """Build a package zip from a metadata folder in either Metadata API or Salesforce DX format."""

    transforms: T.List[SourceTransform] = []

    def __init__(
        self,
        *,
        path=None,
        zf: T.Optional[zipfile.ZipFile] = None,
        options=None,
        logger=None,
        name=None,
        transforms: T.Optional[T.List[SourceTransform]] = None,
    ):
        self.options = options or {}
        self.logger = logger or DEFAULT_LOGGER

        self.zf = zf

        if self.zf is None:
            self._open_zip()
        if path is not None:
            self._add_files_to_package(path)
        if transforms:
            self.transforms = transforms

        self._process()

    @classmethod
    def from_zipfile(
        cls,
        zf: zipfile.ZipFile,
        *,
        path=None,
        options=None,
        logger=None,
        transforms: T.Optional[T.List[SourceTransform]] = None,
    ):
        """Start with an existing zipfile rather than a filesystem folder."""
        return cls(
            zf=zf, path=path, options=options, logger=logger, transforms=transforms
        )

    def _add_files_to_package(self, path):
        for file_path in self._find_files_to_package(path):
            relpath = str(file_path.relative_to(path)).replace(os.sep, "/")
            self.zf.write(file_path, arcname=relpath)

    def _find_files_to_package(self, path):
        """Generator of paths to include in the package.

        Walks through all directories and files in path,
        filtering using _include_directory and _include_file
        """
        for root, _, files in os.walk(path):
            root_parts = pathlib.Path(root).relative_to(path).parts
            if self._include_directory(root_parts):
                for f in files:
                    if self._include_file(root_parts, f):
                        yield pathlib.Path(root, f)

    def _include_directory(self, root_parts):
        """Return boolean for whether this directory should be included in the package."""
        # include root
        if len(root_parts) == 0:
            return True

        # don't include lwc tests
        if root_parts[0] == "lwc" and any(part.startswith("__") for part in root_parts):
            return False

        # include everything else
        return True

    def _include_file(self, root_parts, f):
        """Return boolean for whether this file should be included in the package."""
        if len(root_parts) and root_parts[0] == "lwc":
            # only include expected file extensions within lwc components
            return f.lower().endswith((".js", ".js-meta.xml", ".html", ".css", ".svg"))
        return True

    def _process(self):
        # We have to close the existing zipfile and reopen it before processing;
        # otherwise we hit a bug in Windows where ZipInfo objects have the wrong path separators.
        fp = self.zf.fp
        self.zf.close()
        self.zf = zipfile.ZipFile(fp, "r")

        transforms = []

        # User-specified transforms
        transforms.extend(self.transforms)

        # Default transforms (backwards-compatible)
        # Namespace injection
        transforms.append(
            NamespaceInjectionTransform(NamespaceInjectionOptions(**self.options))
        )
        # -meta.xml cleaning
        if self.options.get("clean_meta_xml", True):
            transforms.append(CleanMetaXMLTransform())
        # Static resource bundling
        relpath = self.options.get("static_resource_path")
        if relpath and os.path.exists(relpath):
            transforms.append(
                BundleStaticResourcesTransform(
                    BundleStaticResourcesOptions(static_resource_path=relpath)
                )
            )
        # Feature Parameter stripping (Unlocked Packages only)
        if self.options.get("package_type") == "Unlocked":
            transforms.append(RemoveFeatureParametersTransform())

        for t in transforms:
            new_zipfile = t.process(self.zf, self.logger)
            if new_zipfile != self.zf:
                # Ensure that zipfiles are closed (in case they're filesystem resources)
                try:
                    self.zf.close()
                except ValueError:  # Attempt to close a closed ZF (on Windows)
                    pass
                self.zf = new_zipfile


class CreatePackageZipBuilder(BasePackageZipBuilder):
    def __init__(self, name, api_version):
        if not name:
            raise ValueError("You must provide a name to create a package")
        if not api_version:
            raise ValueError("You must provide an api_version to create a package")
        self.name = name
        self.api_version = api_version

        self._open_zip()
        self._populate_zip()

    def _populate_zip(self):
        package_xml = FULL_NAME_PACKAGE_XML.format(escape(self.name), self.api_version)
        self._write_package_xml(package_xml)


class InstallPackageZipBuilder(BasePackageZipBuilder):
    api_version = "43.0"

    def __init__(
        self, namespace, version, activateRSS=False, password=None, securityType="FULL"
    ):
        if not namespace:
            raise ValueError("You must provide a namespace to install a package")
        if not version:
            raise ValueError("You must provide a version to install a package")
        self.namespace = namespace
        self.version = version
        self.activateRSS = activateRSS
        self.password = password
        self.securityType = securityType

        self._open_zip()
        self._populate_zip()

    def _populate_zip(self):
        package_xml = INSTALLED_PACKAGE_PACKAGE_XML.format(
            namespace=self.namespace, version=self.api_version
        )
        self._write_package_xml(package_xml)

        activateRSS = "true" if self.activateRSS else "false"
        password = (
            "<password>{}</password>".format(html.escape(self.password))
            if self.password
            else ""
        )
        installed_package = INSTALLED_PACKAGE.format(
            self.version, activateRSS, self.securityType, password
        )
        self._write_file(
            "installedPackages/{}.installedPackage".format(self.namespace),
            installed_package,
        )


class DestructiveChangesZipBuilder(BasePackageZipBuilder):
    def __init__(self, destructive_changes, version):
        self.destructive_changes = destructive_changes
        self.version = version

        self._open_zip()
        self._populate_zip()

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

        self._open_zip()
        self._populate_zip()
