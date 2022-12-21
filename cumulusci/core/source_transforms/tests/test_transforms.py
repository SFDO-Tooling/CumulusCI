import io
import os
import typing as T
import zipfile
from pathlib import Path, PurePosixPath
from unittest import mock
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.core.source_transforms.transforms import (
    CleanMetaXMLTransform,
    FindReplaceIdAPI,
    FindReplaceTransform,
    FindReplaceTransformOptions,
    NamespaceInjectionTransform,
    RemoveFeatureParametersTransform,
    SourceTransformList,
    SourceTransformSpec,
    StripUnwantedComponentsOptions,
    StripUnwantedComponentTransform,
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
                    outcome = this.encode("utf-8").replace(
                        b"\r\n", b"\n"
                    ) == other.replace(
                        b"\r\n", b"\n"
                    )  # Replacing windows new line characters with Unix new characters
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


def test_namespace_inject(task_context):
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path(
                    "___NAMESPACE___Foo.cls"
                ): "System.debug('%%%NAMESPACE%%%blah%%%NAMESPACED_ORG%%%');"
            }
        ).as_zipfile(),
        options={"namespace_inject": "ns", "unmanaged": False},
        context=task_context,
    )
    assert ZipFileSpec({Path("ns__Foo.cls"): "System.debug('ns__blah');"}) == builder.zf


def test_namespace_inject__unmanaged(task_context):
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {Path("___NAMESPACE___Foo.cls"): "System.debug('%%%NAMESPACE%%%blah');"}
        ).as_zipfile(),
        options={"namespace_inject": "ns"},
        context=task_context,
    )
    assert ZipFileSpec({Path("Foo.cls"): "System.debug('blah');"}) == builder.zf


def test_namespace_inject__namespaced_org(task_context):
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path(
                    "___NAMESPACE___Foo.cls"
                ): "System.debug('%%%NAMESPACED_ORG%%%blah');"
            }
        ).as_zipfile(),
        options={"namespace_inject": "ns", "namespaced_org": True},
        context=task_context,
    )
    assert ZipFileSpec({Path("Foo.cls"): "System.debug('ns__blah');"}) == builder.zf


def test_namespace_strip(task_context):
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec({Path("ns__Foo.cls"): "System.debug('ns__blah');"}).as_zipfile(),
        options={"namespace_strip": "ns", "unmanaged": False},
        context=task_context,
    )
    assert ZipFileSpec({Path("Foo.cls"): "System.debug('blah');"}) == builder.zf


def test_namespace_tokenize(task_context):
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec({Path("ns__Foo.cls"): "System.debug('ns__blah');"}).as_zipfile(),
        options={"namespace_tokenize": "ns", "unmanaged": False},
        context=task_context,
    )
    assert (
        ZipFileSpec(
            {Path("___NAMESPACE___Foo.cls"): "System.debug('%%%NAMESPACE%%%blah');"}
        )
        == builder.zf
    )


def test_namespace_injection_ignores_binary(task_context):
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path("ns__Foo.cls"): "System.debug('ns__blah');",
                Path("b.staticResource"): b"ns__\xFF\xFF",
            }
        ).as_zipfile(),
        options={"namespace_tokenize": "ns", "unmanaged": False},
        context=task_context,
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


def test_clean_meta_xml(task_context):
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
        ZipFileSpec({Path("classes/Foo.cls-meta.xml"): xml_data}).as_zipfile(),
        context=task_context,
    )
    assert ZipFileSpec({Path("classes/Foo.cls-meta.xml"): xml_data_clean}) == builder.zf


def test_clean_meta_xml__inactive(task_context):
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
        context=task_context,
    )
    assert ZipFileSpec({Path("classes") / "Foo.cls-meta.xml": xml_data}) == builder.zf


def test_remove_feature_parameters(task_context):
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
        context=task_context,
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


def test_remove_feature_parameters__inactive(task_context):
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
        context=task_context,
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


def test_bundle_static_resources(task_context):
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
            context=task_context,
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


def test_find_replace_static(task_context):
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path("Foo.cls"): "System.debug('blah');",
            }
        ).as_zipfile(),
        context=task_context,
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


def test_find_replace_environ(task_context):
    with mock.patch.dict(os.environ, {"INSERT_TEXT": "ye"}):
        builder = MetadataPackageZipBuilder.from_zipfile(
            ZipFileSpec(
                {
                    Path("Foo.cls"): "System.debug('blah');",
                }
            ).as_zipfile(),
            context=task_context,
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


def test_find_replace_environ__not_found(task_context):
    assert "INSERT_TEXT" not in os.environ
    with pytest.raises(TaskOptionsError):
        MetadataPackageZipBuilder.from_zipfile(
            ZipFileSpec(
                {
                    Path("Foo.cls"): "System.debug('blah');",
                }
            ).as_zipfile(),
            context=task_context,
            transforms=[
                FindReplaceTransform(
                    FindReplaceTransformOptions.parse_obj(
                        {"patterns": [{"find": "bl", "replace_env": "INSERT_TEXT"}]}
                    )
                )
            ],
        )


def test_find_replace_filtered(task_context):
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path("classes") / "Foo.cls": "System.debug('blah');",
                Path("Bar.cls"): "System.debug('blah');",
            }
        ).as_zipfile(),
        context=task_context,
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


def test_find_replace_multiple(task_context):
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path("classes") / "Foo.cls": "System.debug('blah');",
                Path("Bar.cls"): "System.debug('blah');",
            }
        ).as_zipfile(),
        context=task_context,
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


def test_find_replace_current_user(task_context):
    options = FindReplaceTransformOptions.parse_obj(
        {
            "patterns": [
                {
                    "find": "%%%CURRENT_USER%%%",
                },
            ]
        }
    )
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path("classes") / "Foo.cls": "System.debug('%%%CURRENT_USER%%%');",
                Path("Bar.cls"): "System.debug('blah');",
            }
        ).as_zipfile(),
        context=task_context,
        transforms=[FindReplaceTransform(options)],
    )

    expected_username = task_context.org_config.username
    assert (
        ZipFileSpec(
            {
                Path("classes") / "Foo.cls": f"System.debug('{expected_username}');",
                Path("Bar.cls"): "System.debug('blah');",
            }
        )
        == builder.zf
    )


@pytest.mark.parametrize("api", [FindReplaceIdAPI.REST, FindReplaceIdAPI.TOOLING])
def test_find_replace_id(api):
    context = mock.Mock()
    result = {"totalSize": 1, "records": [{"Id": "00D"}]}
    context.org_config.salesforce_client.query.return_value = result
    context.org_config.tooling.query.return_value = result
    options = FindReplaceTransformOptions.parse_obj(
        {
            "patterns": [
                {
                    "find": "00Y",
                    "replace_record_id_query": "SELECT Id FROM Account WHERE name='Initech Corp.'",
                    "api": api,
                },
            ]
        }
    )
    builder = MetadataPackageZipBuilder.from_zipfile(
        ZipFileSpec(
            {
                Path("classes") / "Foo.cls": "System.debug('00Y');",
                Path("Bar.cls"): "System.debug('blah');",
            }
        ).as_zipfile(),
        context=context,
        transforms=[FindReplaceTransform(options)],
    )

    assert (
        ZipFileSpec(
            {
                Path("classes") / "Foo.cls": "System.debug('00D');",
                Path("Bar.cls"): "System.debug('blah');",
            }
        )
        == builder.zf
    )


def test_find_replace_id__bad_query_result():
    context = mock.Mock()
    result = {"totalSize": 0}
    context.org_config.salesforce_client.query.return_value = result
    options = FindReplaceTransformOptions.parse_obj(
        {
            "patterns": [
                {
                    "find": "00Y",
                    "replace_record_id_query": "SELECT Id FROM Account WHERE name='Initech Corp.'",
                },
            ]
        }
    )
    with pytest.raises(CumulusCIException):
        MetadataPackageZipBuilder.from_zipfile(
            ZipFileSpec(
                {
                    Path("classes") / "Foo.cls": "System.debug('00Y');",
                    Path("Bar.cls"): "System.debug('blah');",
                }
            ).as_zipfile(),
            context=context,
            transforms=[FindReplaceTransform(options)],
        )


def test_find_replace_id__no_id_returned():
    context = mock.Mock()
    result = {"totalSize": 1, "records": [{"name": "foo"}]}
    context.org_config.salesforce_client.query.return_value = result
    options = FindReplaceTransformOptions.parse_obj(
        {
            "patterns": [
                {
                    "find": "00Y",
                    "replace_record_id_query": "SELECT Id FROM Account WHERE name='Initech Corp.'",
                },
            ]
        }
    )
    with pytest.raises(CumulusCIException):
        MetadataPackageZipBuilder.from_zipfile(
            ZipFileSpec(
                {
                    Path("classes") / "Foo.cls": "System.debug('00Y');",
                    Path("Bar.cls"): "System.debug('blah');",
                }
            ).as_zipfile(),
            context=context,
            transforms=[FindReplaceTransform(options)],
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


def test_strip_unwanted_files(task_context):
    """
    This test covers all strip options available during deployment.
    It covers below scenarios:
        1. Class files - Removes Bar.class and keeps Foo.class file
        2. Aura files - Removes aura2.cmp file and keeps aura1.cmp file
        3. Report files - Keeps TestReports folder, FooReport.report file and deletes BlahReport.report file
        4. Custom object files - Removes Test2__c.CustomField2__c field from Test2__c.object file
        5. Lightning bundle - Removes lwc2.cmp file from lwc folder
    """

    with temporary_dir() as temp_dir:
        package_xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>TestPackage</fullName>
    <types>
        <members>Foo</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>bundle1</members>
        <name>AuraDefinitionBundle</name>
    </types>
    <types>
        <members>TestReports</members>
        <members>TestReports/FooReport</members>
        <name>Report</name>
    </types>
    <types>
        <members>Test1__c.CustomField1__c</members>
        <members>Test1__c.CustomField2__c</members>
        <members>Test2__c.CustomField1__c</members>
        <name>CustomField</name>
    </types>
    <types>
        <members>Test1__c</members>
        <members>Test2__c</members>
        <name>CustomObject</name>
    </types>
        <types>
        <members>lwcBundle1</members>
        <name>LightningComponentBundle</name>
    </types>
    <version>43.0</version>
</Package>
"""
        meta_xml = """<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>56.0</apiVersion>
</ApexClass>"""

        object_xml_data = """<?xml version='1.0' encoding='UTF-8'?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>CustomField1__c</fullName>
        <externalId>false</externalId>
        <label>Expected Completion Date</label>
        <required>false</required>
        <trackTrending>false</trackTrending>
        <type>Text</type>
    </fields>
    <fields>
        <fullName>CustomField2__c</fullName>
        <externalId>false</externalId>
        <label>Expected Completion Date</label>
        <required>false</required>
        <trackTrending>false</trackTrending>
        <type>Text</type>
    </fields>
</CustomObject>"""
        strip_object2_xml_data = """<?xml version='1.0' encoding='UTF-8'?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>CustomField1__c</fullName>
        <externalId>false</externalId>
        <label>Expected Completion Date</label>
        <required>false</required>
        <trackTrending>false</trackTrending>
        <type>Text</type>
    </fields>
    </CustomObject>"""
        td = Path(temp_dir)

        (td / "package_test.xml").write_text(package_xml_data)
        builder = MetadataPackageZipBuilder.from_zipfile(
            ZipFileSpec(
                {
                    Path(os.path.join("aura", "bundle1", "aura1.cmp")): "Comp 1",
                    Path(os.path.join("aura", "bundle2", "aura2.cmp")): "Comp 2",
                    Path(os.path.join("classes", "Foo.cls")): "System.debug('foo');",
                    Path(os.path.join("classes", "Foo.cls-meta.xml")): meta_xml,
                    Path(os.path.join("classes", "Bar.cls")): "System.debug('bar');",
                    Path(os.path.join("classes", "Bar.cls-meta.xml")): meta_xml,
                    Path(os.path.join("reports", "TestReports-meta.xml")): meta_xml,
                    Path(
                        os.path.join("reports", "TestReports"), "FooReport.report"
                    ): "Foo Report",
                    Path(
                        os.path.join("reports", "TestReports"), "BlahReport.report"
                    ): "Blah Report",
                    Path(os.path.join("objects", "Test1__c.object")): object_xml_data,
                    Path(os.path.join("objects", "Test2__c.object")): object_xml_data,
                    Path(os.path.join("lwc", "lwcBundle1", "lwc1.cmp")): "Comp 1",
                    Path(os.path.join("lwc", "lwcBundle2", "lwc2.cmp")): "Comp 2",
                }
            ).as_zipfile(),
            context=task_context,
            transforms=[
                StripUnwantedComponentTransform(
                    StripUnwantedComponentsOptions.parse_obj(
                        {"package_xml": "package_test.xml"}
                    )
                )
            ],
        )

        assert (
            ZipFileSpec(
                {
                    Path(os.path.join("aura", "bundle1", "aura1.cmp")): "Comp 1",
                    Path(os.path.join("classes", "Foo.cls")): "System.debug('foo');",
                    Path(os.path.join("classes", "Foo.cls-meta.xml")): meta_xml,
                    Path(os.path.join("reports", "TestReports-meta.xml")): meta_xml,
                    Path(
                        os.path.join("reports", "TestReports"), "FooReport.report"
                    ): "Foo Report",
                    Path(os.path.join("objects", "Test1__c.object")): object_xml_data,
                    Path(
                        os.path.join("objects", "Test2__c.object")
                    ): strip_object2_xml_data,
                    Path(os.path.join("lwc", "lwcBundle1", "lwc1.cmp")): "Comp 1",
                    Path("package.xml"): package_xml_data,
                }
            )
            == builder.zf
        )
