import io
import os
import typing as T
import zipfile
from pathlib import Path, PurePosixPath
from unittest import mock
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.source_transforms.transforms import (
    CleanMetaXMLTransform,
    FindReplaceTransform,
    FindReplaceTransformOptions,
    NamespaceInjectionTransform,
    RemoveFeatureParametersTransform,
    SourceTransformList,
    SourceTransformSpec,
)
from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder
from cumulusci.utils import temporary_dir


class ZipFileSpec:
    content: T.Dict[Path, T.Union[str, bytes, "ZipFileSpec"]]

    def __init__(self, content: T.Dict[Path, T.Union[str, bytes, "ZipFileSpec"]]):
        self.content = content

    def as_zipfile(self) -> ZipFile:
        zip_dest = ZipFile(io.BytesIO(), "w", zipfile.ZIP_DEFLATED)
        for path, content in self.content.items():
            if isinstance(content, ZipFileSpec):
                raise Exception("Generating nested zipfiles is not supported")
            zip_dest.writestr(str(path), content)

        # Zipfile must be returned in open state to be used by MetadataPackageZipBuilder
        return zip_dest

    def __eq__(self, other):
        # When we write zipfiles, Windows paths are normalized to POSIX paths.
        # But when we read, we must construct and supply the POSIX path -
        # Windows-style paths _aren't_ normalized on read.

        if isinstance(other, ZipFileSpec):
            return other.content == self.content
        elif isinstance(other, ZipFile):
            fp = other.fp
            other.close()
            other = ZipFile(fp, "r")  # type: ignore

            def element_equal(this, other):
                if isinstance(this, ZipFileSpec):
                    outcome = this == ZipFile(
                        io.BytesIO(other), "r", zipfile.ZIP_DEFLATED
                    )
                elif isinstance(this, str):
                    outcome = this.encode("utf-8") == other
                else:
                    outcome = this == other

                if not outcome:
                    print(f"Found zipfile members unequal: {this}, {other}")
                return outcome

            return set(other.namelist()) == set(
                [str(PurePosixPath(s)) for s in self.content.keys()]
            ) and all(
                element_equal(self.content[name], other.read(str(PurePosixPath(name))))
                for name in self.content.keys()
            )
        else:
            return False


def test_namespace_inject():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path(
                    "___NAMESPACE___Foo.cls"
                ): "System.debug('%%%NAMESPACE%%%blah%%%NAMESPACED_ORG%%%');"
            }
        ).as_zipfile(),
        options={"namespace_inject": "ns", "unmanaged": False},
    )
    assert ZipFileSpec({Path("ns__Foo.cls"): "System.debug('ns__blah');"}) == builder.zf


def test_namespace_inject__unmanaged():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {Path("___NAMESPACE___Foo.cls"): "System.debug('%%%NAMESPACE%%%blah');"}
        ).as_zipfile(),
        options={"namespace_inject": "ns"},
    )
    assert ZipFileSpec({Path("Foo.cls"): "System.debug('blah');"}) == builder.zf


def test_namespace_inject__namespaced_org():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path(
                    "___NAMESPACE___Foo.cls"
                ): "System.debug('%%%NAMESPACED_ORG%%%blah');"
            }
        ).as_zipfile(),
        options={"namespace_inject": "ns", "namespaced_org": True},
    )
    assert ZipFileSpec({Path("Foo.cls"): "System.debug('ns__blah');"}) == builder.zf


def test_namespace_strip():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec({Path("ns__Foo.cls"): "System.debug('ns__blah');"}).as_zipfile(),
        options={"namespace_strip": "ns", "unmanaged": False},
    )
    assert ZipFileSpec({Path("Foo.cls"): "System.debug('blah');"}) == builder.zf


def test_namespace_tokenize():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec({Path("ns__Foo.cls"): "System.debug('ns__blah');"}).as_zipfile(),
        options={"namespace_tokenize": "ns", "unmanaged": False},
    )
    assert (
        ZipFileSpec(
            {Path("___NAMESPACE___Foo.cls"): "System.debug('%%%NAMESPACE%%%blah');"}
        )
        == builder.zf
    )


def test_namespace_injection_ignores_binary():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path("ns__Foo.cls"): "System.debug('ns__blah');",
                Path("b.staticResource"): b"ns__\xFF\xFF",
            }
        ).as_zipfile(),
        options={"namespace_tokenize": "ns", "unmanaged": False},
    )
    assert (
        ZipFileSpec(
            {
                Path("___NAMESPACE___Foo.cls"): "System.debug('%%%NAMESPACE%%%blah');",
                Path("b.staticResource"): b"ns__\xFF\xFF",
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
        ZipFileSpec({Path("classes/Foo.cls-meta.xml"): xml_data}).as_zipfile()
    )
    assert ZipFileSpec({Path("classes/Foo.cls-meta.xml"): xml_data_clean}) == builder.zf


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
        ZipFileSpec({Path("classes") / "Foo.cls-meta.xml": xml_data}).as_zipfile(),
        options={"clean_meta_xml": False},
    )
    assert ZipFileSpec({Path("classes") / "Foo.cls-meta.xml": xml_data}) == builder.zf


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
                Path("featureParameters") / "blah.featureParameterInteger": "foo",
                Path("package.xml"): xml_data,
                Path("classes") / "MyClass.cls": "blah",
            }
        ).as_zipfile(),
        options={"package_type": "Unlocked"},
    )
    assert (
        ZipFileSpec(
            {
                Path("package.xml"): xml_data_clean,
                Path("classes") / "MyClass.cls": "blah",
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
                Path("featureParameters") / "blah.featureParameterInteger": "foo",
                Path("package.xml"): xml_data,
                Path("classes") / "MyClass.cls": "blah",
            }
        ).as_zipfile(),
    )
    assert (
        ZipFileSpec(
            {
                Path("featureParameters") / "blah.featureParameterInteger": "foo",
                Path("package.xml"): xml_data,
                Path("classes") / "MyClass.cls": "blah",
            }
        )
        == builder.zf
    )


def test_bundle_static_resources():
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>TestPackage</fullName>
    <types>
        <members>MyClass</members>
        <name>ApexClass</name>
    </types>
    <version>43.0</version>
</Package>
"""

    xml_data_with_statics = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>TestPackage</fullName>
    <types>
        <members>MyClass</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>bar</members>
        <members>foo</members>
        <name>StaticResource</name>
    </types>
    <version>43.0</version>
</Package>
"""

    with temporary_dir() as td_path:
        # Construct a directory with zippable Static Resource data
        # Because of how the static resource bundling works, this needs
        # to be a real filesystem directory.

        td = Path(td_path)

        statics_dir = td / "statics"
        statics_dir.mkdir()
        (statics_dir / "foo.resource-meta.xml").write_text("foo")
        (statics_dir / "bar.resource-meta.xml").write_text("bar")
        (statics_dir / "foo").mkdir()
        (statics_dir / "foo" / "foo.html").write_text("foo html")
        (statics_dir / "bar").mkdir()
        (statics_dir / "bar" / "bar.html").write_text("bar html")

        builder = MetadataPackageZipBuilder.from_zipfile(
            ZipFileSpec(
                {
                    Path("package.xml"): xml_data,
                    Path("classes") / "MyClass.cls": "blah",
                }
            ).as_zipfile(),
            options={"static_resource_path": str(statics_dir)},
        )

        foo_spec = ZipFileSpec(
            {
                Path("foo.html"): "foo html",
            }
        )
        bar_spec = ZipFileSpec({Path("bar.html"): "bar html"})
        compare_spec = ZipFileSpec(
            {
                Path("staticresources") / "foo.resource": foo_spec,
                Path("staticresources") / "foo.resource-meta.xml": "foo",
                Path("staticresources") / "bar.resource": bar_spec,
                Path("staticresources") / "bar.resource-meta.xml": "bar",
                Path("package.xml"): xml_data_with_statics,
                Path("classes") / "MyClass.cls": "blah",
            }
        )

        # Close and reopen the zipfile to avoid issues on Windows.
        fp = builder.zf.fp  # type: ignore
        builder.zf.close()  # type: ignore
        zf = ZipFile(fp, "r")  # type: ignore

        assert compare_spec == zf


def test_find_replace_static():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path("Foo.cls"): "System.debug('blah');",
            }
        ).as_zipfile(),
        transforms=[
            FindReplaceTransform(
                FindReplaceTransformOptions.parse_obj(
                    {"patterns": [{"find": "bl", "replace": "ye"}]}
                )
            )
        ],
    )

    assert (
        ZipFileSpec(
            {
                Path("Foo.cls"): "System.debug('yeah');",
            }
        )
        == builder.zf
    )


def test_find_replace_environ():
    with mock.patch.dict(os.environ, {"INSERT_TEXT": "ye"}):
        builder = MetadataPackageZipBuilder.from_zipfile(
            ZipFileSpec(
                {
                    Path("Foo.cls"): "System.debug('blah');",
                }
            ).as_zipfile(),
            transforms=[
                FindReplaceTransform(
                    FindReplaceTransformOptions.parse_obj(
                        {"patterns": [{"find": "bl", "replace_env": "INSERT_TEXT"}]}
                    )
                )
            ],
        )

        assert (
            ZipFileSpec(
                {
                    Path("Foo.cls"): "System.debug('yeah');",
                }
            )
            == builder.zf
        )


def test_find_replace_environ__not_found():
    assert "INSERT_TEXT" not in os.environ
    with pytest.raises(TaskOptionsError):
        MetadataPackageZipBuilder.from_zipfile(
            ZipFileSpec(
                {
                    Path("Foo.cls"): "System.debug('blah');",
                }
            ).as_zipfile(),
            transforms=[
                FindReplaceTransform(
                    FindReplaceTransformOptions.parse_obj(
                        {"patterns": [{"find": "bl", "replace_env": "INSERT_TEXT"}]}
                    )
                )
            ],
        )


def test_find_replace_filtered():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path("classes") / "Foo.cls": "System.debug('blah');",
                Path("Bar.cls"): "System.debug('blah');",
            }
        ).as_zipfile(),
        transforms=[
            FindReplaceTransform(
                FindReplaceTransformOptions.parse_obj(
                    {
                        "patterns": [
                            {"find": "bl", "replace": "ye", "paths": ["classes"]}
                        ]
                    }
                )
            )
        ],
    )

    assert (
        ZipFileSpec(
            {
                Path("classes") / "Foo.cls": "System.debug('yeah');",
                Path("Bar.cls"): "System.debug('blah');",
            }
        )
        == builder.zf
    )


def test_find_replace_multiple():
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path("classes") / "Foo.cls": "System.debug('blah');",
                Path("Bar.cls"): "System.debug('blah');",
            }
        ).as_zipfile(),
        transforms=[
            FindReplaceTransform(
                FindReplaceTransformOptions.parse_obj(
                    {
                        "patterns": [
                            {"find": "bl", "replace": "ye", "paths": ["classes"]},
                            {"find": "ye", "replace": "ha"},
                        ]
                    }
                )
            )
        ],
    )

    assert (
        ZipFileSpec(
            {
                Path("classes") / "Foo.cls": "System.debug('haah');",
                Path("Bar.cls"): "System.debug('blah');",
            }
        )
        == builder.zf
    )


def test_source_transform_parsing():
    tl = SourceTransformList.parse_obj(
        [
            "clean_meta_xml",
            {"transform": "inject_namespace", "options": {"namespace_tokenize": "foo"}},
            {"transform": "remove_feature_parameters"},
        ]
    )

    assert len(tl.__root__) == 3
    assert isinstance(tl.__root__[0], SourceTransformSpec)
    assert isinstance(tl.__root__[1], SourceTransformSpec)
    assert tl.__root__[1].parsed_options() is not None
    assert isinstance(tl.__root__[2], SourceTransformSpec)
    assert tl.__root__[2].parsed_options() is None

    tf = tl.as_transforms()

    assert isinstance(tf[0], CleanMetaXMLTransform)
    assert isinstance(tf[1], NamespaceInjectionTransform)
    assert isinstance(tf[2], RemoveFeatureParametersTransform)
    assert tf[1].options.namespace_tokenize == "foo"


def test_source_transform_parsing__bad_transform():
    with pytest.raises(ValidationError) as e:
        SourceTransformList.parse_obj(
            [
                "destroy_the_things",
            ]
        )

        assert "destroy_the_things is not valid" in str(e)
