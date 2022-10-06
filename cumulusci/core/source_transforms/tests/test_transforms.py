import io
import typing as T
import zipfile
from re import L
from zipfile import ZipFile

from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder


class ZipFileSpec:
    content: dict[str, T.Union[str, bytes]]

    def __init__(self, content: dict[str, T.Union[str, bytes]]):
        self.content = content

    def as_zipfile(self) -> ZipFile:
        zip_dest = ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
        for path, content in self.content.items():
            zip_dest.writestr(path, content)

        # Zipfile must be returned in open state to be used by MetadataPackageZipBuilder
        return zip_dest

    def __eq__(self, other):
        if isinstance(other, ZipFileSpec):
            return other.content == self.content
        elif isinstance(other, ZipFile):
            return set(other.namelist()) == set(self.content.keys()) and all(
                other.read(name)
                == (
                    self.content[name]
                    if type(self.content[name]) is bytes
                    else self.content[name].encode("utf-8")  # type: ignore
                )
                for name in self.content
            )
        else:
            return False


def test_namespace_inject():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                "___NAMESPACE___Foo.cls": "System.debug('%%%NAMESPACE%%%blah%%%NAMESPACED_ORG%%%');"
            }
        ).as_zipfile(),
        options={"namespace_inject": "ns", "unmanaged": False},
    )
    assert ZipFileSpec({"ns__Foo.cls": "System.debug('ns__blah');"}) == builder.zf


def test_namespace_inject__unmanaged():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {"___NAMESPACE___Foo.cls": "System.debug('%%%NAMESPACE%%%blah');"}
        ).as_zipfile(),
        options={"namespace_inject": "ns"},
    )
    assert ZipFileSpec({"Foo.cls": "System.debug('blah');"}) == builder.zf


def test_namespace_inject__namespaced_org():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {"___NAMESPACE___Foo.cls": "System.debug('%%%NAMESPACED_ORG%%%blah');"}
        ).as_zipfile(),
        options={"namespace_inject": "ns", "namespaced_org": True},
    )
    assert ZipFileSpec({"Foo.cls": "System.debug('ns__blah');"}) == builder.zf


def test_namespace_strip():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec({"ns__Foo.cls": "System.debug('ns__blah');"}).as_zipfile(),
        options={"namespace_strip": "ns", "unmanaged": False},
    )
    assert ZipFileSpec({"Foo.cls": "System.debug('blah');"}) == builder.zf


def test_namespace_tokenize():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec({"ns__Foo.cls": "System.debug('ns__blah');"}).as_zipfile(),
        options={"namespace_tokenize": "ns", "unmanaged": False},
    )
    assert (
        ZipFileSpec({"___NAMESPACE___Foo.cls": "System.debug('%%%NAMESPACE%%%blah');"})
        == builder.zf
    )


def test_namespace_injection_ignores_binary():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                "ns__Foo.cls": "System.debug('ns__blah');",
                "b.staticResource": b"ns__\xFF\xFF",
            }
        ).as_zipfile(),
        options={"namespace_tokenize": "ns", "unmanaged": False},
    )
    assert (
        ZipFileSpec(
            {
                "___NAMESPACE___Foo.cls": "System.debug('%%%NAMESPACE%%%blah');",
                "b.staticResource": b"ns__\xFF\xFF",
            }
        )
        == builder.zf
    )


def test_clean_meta_xml():
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>56.0</apiVersion>
    <packageVersions>
        <majorNumber>3</majorNumber>
        <minorNumber>11</minorNumber>
        <namespace>npe01</namespace>
    </packageVersions>
</ApexClass>
"""

    xml_data_clean = """<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>56.0</apiVersion>
    </ApexClass>"""

    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec({"classes/Foo.cls-meta.xml": xml_data}).as_zipfile()
    )
    assert ZipFileSpec({"classes/Foo.cls-meta.xml": xml_data_clean}) == builder.zf


def test_clean_meta_xml__inactive():
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>56.0</apiVersion>
    <packageVersions>
        <majorNumber>3</majorNumber>
        <minorNumber>11</minorNumber>
        <namespace>npe01</namespace>
    </packageVersions>
</ApexClass>
"""

    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec({"classes/Foo.cls-meta.xml": xml_data}).as_zipfile(),
        options={"clean_meta_xml": False},
    )
    assert ZipFileSpec({"classes/Foo.cls-meta.xml": xml_data}) == builder.zf


def test_remove_feature_parameters():
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>TestPackage</fullName>
    <types>
        <members>MyClass</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>blah</members>
        <name>FeatureParameterInteger</name>
    </types>
    <version>43.0</version>
</Package>"""

    xml_data_clean = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>TestPackage</fullName>
    <types>
        <members>MyClass</members>
        <name>ApexClass</name>
    </types>
    <version>43.0</version>
</Package>
"""

    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                "featureParameters/blah.featureParameterInteger": "foo",
                "package.xml": xml_data,
                "classes/MyClass.cls": "blah",
            }
        ).as_zipfile(),
        options={"package_type": "Unlocked"},
    )
    assert (
        ZipFileSpec(
            {
                "package.xml": xml_data_clean,
                "classes/MyClass.cls": "blah",
            }
        )
        == builder.zf
    )


def test_remove_feature_parameters__inactive():
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>TestPackage</fullName>
    <types>
        <members>MyClass</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>blah</members>
        <name>FeatureParameterInteger</name>
    </types>
    <version>43.0</version>
</Package>"""

    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                "featureParameters/blah.featureParameterInteger": "foo",
                "package.xml": xml_data,
                "classes/MyClass.cls": "blah",
            }
        ).as_zipfile(),
    )
    assert (
        ZipFileSpec(
            {
                "featureParameters/blah.featureParameterInteger": "foo",
                "package.xml": xml_data,
                "classes/MyClass.cls": "blah",
            }
        )
        == builder.zf
    )
