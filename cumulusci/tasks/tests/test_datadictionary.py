import io
import unittest

from unittest.mock import Mock, call, patch, mock_open

from cumulusci.tasks.datadictionary import (
    GenerateDataDictionary,
    Package,
    PackageVersion,
    FieldDetail,
    SObjectDetail,
)
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tests.util import create_project_config
from cumulusci.utils.xml import metadata_tree
from distutils.version import StrictVersion


class test_GenerateDataDictionary(unittest.TestCase):
    def test_version_from_tag_name(self):
        task = create_task(GenerateDataDictionary, {})

        assert task._version_from_tag_name("release/1.1", "release/") == StrictVersion(
            "1.1"
        )

    def test_write_object_results(self):
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))
        v2 = PackageVersion(p, StrictVersion("1.2"))
        task.package_versions = {p: [v2.version, v.version]}
        task.sobjects = {
            "test__Test__c": [SObjectDetail(v, "test__Test__c", "Test", "Description")]
        }

        f = io.StringIO()
        task._write_object_results(f)

        f.seek(0)
        result = f.read()
        print(result)
        assert (
            result
            == "Object Label,Object API Name,Object Description,Version Introduced,Version Deleted\r\nTest,test__Test__c,Description,Test 1.1,Test 1.2\r\n"
        )

    def test_write_field_results(self):
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))
        v2 = PackageVersion(p, StrictVersion("1.2"))
        task.package_versions = {p: [v2.version, v.version]}
        task.fields = {
            "test__Test__c.test__Type__c": [
                FieldDetail(
                    v,
                    "test__Test__c",
                    "test__Type__c",
                    "Type",
                    "Picklist",
                    "Help",
                    "Description",
                    "Foo; Bar",
                    "",
                ),
                FieldDetail(
                    v2,
                    "test__Test__c",
                    "test__Type__c",
                    "Type",
                    "Picklist",
                    "New Help",
                    "Description",
                    "Foo; Bar; New Value",
                    "",
                ),
            ],
            "test__Test__c.test__Account__c": [
                FieldDetail(
                    v,
                    "test__Test__c",
                    "test__Account__c",
                    "Account",
                    "Lookup to Account",
                    "Help",
                    "Description",
                    "",
                    "",
                )
            ],
        }

        f = io.StringIO()
        task._write_field_results(f)
        f.seek(0)
        result = f.read()
        print(result)
        assert result == (
            "Object API Name,Field Label,Field API Name,Type,Help Text,Field Description,Allowed Values,Length,Version Introduced,Version Allowed Values Last Changed,Version Help Text Last Changed,Version Deleted\r\n"
            "test__Test__c,Type,test__Type__c,Picklist,New Help,Description,Foo; Bar; New Value,,Test 1.1,Test 1.2,Test 1.2,\r\n"
            "test__Test__c,Account,test__Account__c,Lookup to Account,Help,Description,,,Test 1.1,,,Test 1.2\r\n"
        )

    def test_process_field_element__new(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account__c</fullName>
    <label>Account</label>
    <type>Lookup</type>
    <referenceTo>Account</referenceTo>
</CustomField>
"""
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        task._init_schema()
        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "test__Test__c.test__Account__c" in task.fields
        assert task.fields["test__Test__c.test__Account__c"] == [
            FieldDetail(
                v,
                "test__Test__c",
                "test__Account__c",
                "Account",
                "Lookup to Account",
                "",
                "",
                "",
                "",
            )
        ]

    def test_process_field_element__standard(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account</fullName>
    <label>Account</label>
    <type>Lookup</type>
    <referenceTo>Account</referenceTo>
</CustomField>
"""
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "test__Test__c.Account" not in task.fields

    def test_process_field_element__updated(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account__c</fullName>
    <inlineHelpText>{}</inlineHelpText>
    <label>Account</label>
    <type>Lookup</type>
    <referenceTo>Account</referenceTo>
</CustomField>
"""
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))
        v2 = PackageVersion(p, StrictVersion("1.2"))

        task._process_field_element(
            "test__Test__c",
            metadata_tree.fromstring(xml_source.format("Initial").encode("utf-8")),
            v,
        )

        assert task.fields["test__Test__c.test__Account__c"] == [
            FieldDetail(
                v,
                "test__Test__c",
                "test__Account__c",
                "Account",
                "Lookup to Account",
                "Initial",
                "",
                "",
                "",
            )
        ]

        task._process_field_element(
            "test__Test__c",
            metadata_tree.fromstring(xml_source.format("New").encode("utf-8")),
            v2,
        )
        assert task.fields["test__Test__c.test__Account__c"] == [
            FieldDetail(
                v,
                "test__Test__c",
                "test__Account__c",
                "Account",
                "Lookup to Account",
                "Initial",
                "",
                "",
                "",
            ),
            FieldDetail(
                v2,
                "test__Test__c",
                "test__Account__c",
                "Account",
                "Lookup to Account",
                "New",
                "",
                "",
                "",
            ),
        ]

    def test_process_field_element__valid_values(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Type__c</fullName>
    <label>Type</label>
    <type>Picklist</type>
    <valueSet>
        <valueSetDefinition>
            <value>
                <label>Test 1</label>
                <fullName>Test 1 API</fullName>
            </value>
            <value>
                <label>Test 2</label>
                <fullName>Test 2 API</fullName>
            </value>
        </valueSetDefinition>
    </valueSet>
</CustomField>
"""
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.fields["test__Test__c.test__Type__c"] == [
            FieldDetail(
                v,
                "test__Test__c",
                "test__Type__c",
                "Type",
                "Picklist",
                "",
                "",
                "Test 1; Test 2",
                "",
            )
        ]

    def test_process_field_element__valid_values_old_format(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Type__c</fullName>
    <label>Type</label>
    <type>Picklist</type>
    <picklist>
        <picklistValues>
            <fullName>Test 1</fullName>
            <default>false</default>
        </picklistValues>
        <picklistValues>
            <fullName>Test 2</fullName>
            <default>false</default>
        </picklistValues>
    </picklist>
</CustomField>
"""
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.fields["test__Test__c.test__Type__c"] == [
            FieldDetail(
                v,
                "test__Test__c",
                "test__Type__c",
                "Type",
                "Picklist",
                "",
                "",
                "Test 1; Test 2",
                "",
            )
        ]

    def test_process_field_element__valid_values_global_value_set(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Type__c</fullName>
    <label>Type</label>
    <type>Picklist</type>
    <valueSet>
        <valueSetName>Test Value Set</valueSetName>
    </valueSet>
</CustomField>
"""
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.fields["test__Test__c.test__Type__c"] == [
            FieldDetail(
                v,
                "test__Test__c",
                "test__Type__c",
                "Type",
                "Picklist",
                "",
                "",
                "Global Value Set Test Value Set",
                "",
            )
        ]

    def test_process_object_element(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description</description>
    <label>Test</label>
    <fields>
        <fullName>Type__c</fullName>
        <inlineHelpText>Type of field.</inlineHelpText>
        <description>Desc</description>
        <label>Type</label>
        <type>Text</type>
        <length>128</length>
    </fields>
</CustomObject>"""

        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))
        task._process_object_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.sobjects == {
            "test__Test__c": [SObjectDetail(v, "test__Test__c", "Test", "Description")]
        }
        assert task.fields == {
            "test__Test__c.test__Type__c": [
                FieldDetail(
                    v,
                    "test__Test__c",
                    "test__Type__c",
                    "Type",
                    "Text",
                    "Type of field.",
                    "Desc",
                    "",
                    "128",
                )
            ]
        }

        def test_process_object_element__standard(self):
            xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description</description>
    <label>Test</label>
</CustomObject>"""

            task = create_task(
                GenerateDataDictionary,
                {
                    "object_path": "object.csv",
                    "field_path": "fields.csv",
                    "release_prefix": "rel/",
                },
            )

            task._init_schema()
            p = Package(None, "Test", "test__", "rel/")
            v = PackageVersion(p, StrictVersion("1.1"))
            task._process_object_element(
                "Account", metadata_tree.fromstring(xml_source.encode("utf-8")), v
            )

            assert "Account" not in task.sobjects

    @patch("cumulusci.tasks.datadictionary.metadata_tree.fromstring")
    def test_process_sfdx_release(self, fromstring):
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        zip_file = Mock()
        zip_file.read.return_value = "<test></test>"
        zip_file.namelist.return_value = [
            "force-app/main/default/objects/Child__c.object-meta.xml",
            "force-app/main/default/objects/Child__c/fields/Lookup__c.field-meta.xml",
            "force-app/main/default/objects/Parent__c.object-meta.xml",
            ".gitignore",
            "test__c.object-meta.xml",
        ]
        task._process_object_element = Mock()
        task._process_field_element = Mock()
        task._process_sfdx_release(zip_file, v)

        zip_file.read.assert_has_calls(
            [
                call("force-app/main/default/objects/Child__c.object-meta.xml"),
                call(
                    "force-app/main/default/objects/Child__c/fields/Lookup__c.field-meta.xml"
                ),
                call("force-app/main/default/objects/Parent__c.object-meta.xml"),
            ]
        )

        task._process_object_element.assert_has_calls(
            [
                call("test__Child__c", metadata_tree.fromstring("<test></test>"), v),
                call("test__Parent__c", metadata_tree.fromstring("<test></test>"), v),
            ]
        )
        task._process_field_element.assert_has_calls(
            [call("test__Child__c", metadata_tree.fromstring("<test></test>"), v)]
        )

    @patch("cumulusci.tasks.datadictionary.metadata_tree.fromstring")
    def test_process_mdapi_release(self, fromstring):
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))
        zip_file = Mock()
        zip_file.namelist.return_value = [
            "src/objects/Child__c.object",
            "src/objects/Parent__c.object",
            ".gitignore",
            "test__c.object",
        ]
        zip_file.read.return_value = "<test></test>"
        task._process_object_element = Mock()
        task._process_mdapi_release(zip_file, v)

        zip_file.read.assert_has_calls(
            [call("src/objects/Child__c.object"), call("src/objects/Parent__c.object")]
        )

        task._process_object_element.assert_has_calls(
            [
                call("test__Child__c", metadata_tree.fromstring("<test></test>"), v),
                call("test__Parent__c", metadata_tree.fromstring("<test></test>"), v),
            ]
        )

    @patch("cumulusci.tasks.datadictionary.download_extract_github_from_repo")
    def test_walk_releases__mdapi(self, extract_github):
        project_config = create_project_config()
        project_config.project__git__prefix_release = "rel/"
        project_config.project__name = "Project"
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
            project_config=project_config,
        )
        task._init_schema()

        repo = Mock()
        release = Mock()
        release.draft = False
        release.prerelease = False
        release.tag_name = "rel/1.1"
        repo.releases.return_value = [release]
        task._process_mdapi_release = Mock()
        extract_github.return_value.namelist.return_value = ["src/objects/"]
        p = Package(repo, "Test", "test__", "rel/")

        task._walk_releases(p)

        task._process_mdapi_release.assert_called_once_with(
            extract_github.return_value, PackageVersion(p, StrictVersion("1.1"))
        )

    @patch("cumulusci.tasks.datadictionary.download_extract_github_from_repo")
    def test_walk_releases__sfdx(self, extract_github):
        project_config = create_project_config()
        project_config.project__git__prefix_release = "rel/"
        project_config.project__name = "Project"

        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
            project_config=project_config,
        )
        task._init_schema()

        repo = Mock()
        release = Mock()
        release.draft = False
        release.prerelease = False
        release.tag_name = "rel/1.1"
        repo.releases.return_value = [release]
        task._process_sfdx_release = Mock()
        extract_github.return_value.namelist.return_value = [
            "force-app/main/default/objects/"
        ]
        p = Package(repo, "Test", "test__", "rel/")

        task._walk_releases(p)

        task._process_sfdx_release.assert_called_once_with(
            extract_github.return_value, PackageVersion(p, StrictVersion("1.1"))
        )

    def test_init_schema(self):
        task = create_task(GenerateDataDictionary, {"release_prefix": "rel/"})
        task._init_schema()

        assert task.fields is not None
        assert task.sobjects is not None

    @patch("cumulusci.tasks.datadictionary.download_extract_github_from_repo")
    def test_run_task(self, extract_github):
        # This is an integration test. We mock out `get_repo()` and the filesystem.
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description</description>
    <label>Test</label>
    <fields>
        <fullName>Type__c</fullName>
        <inlineHelpText>Type of field.</inlineHelpText>
        <label>Type</label>
        <type>Text</type>
        <length>255</length>
    </fields>
</CustomObject>"""
        project_config = create_project_config()
        project_config.keychain.get_service = Mock()
        project_config.project__package__name = "Project"
        project_config.project__name = "Project"
        project_config.project__package__namespace = "test"

        task = create_task(GenerateDataDictionary, project_config=project_config)

        task.get_repo = Mock()
        release = Mock()
        release.draft = False
        release.prerelease = False
        release.tag_name = "release/1.1"
        task.get_repo.return_value.releases.return_value = [release]

        extract_github.return_value.namelist.return_value = [
            "src/objects/",
            "src/objects/Test__c.object",
        ]
        extract_github.return_value.read.return_value = xml_source.encode("utf-8")
        m = mock_open()

        with patch("builtins.open", m):
            task()

        m.assert_has_calls(
            [call("Project Objects.csv", "w"), call("Project Fields.csv", "w")],
            any_order=True,
        )
        print(m.return_value.write.call_args_list)
        m.return_value.write.assert_has_calls(
            [
                call(
                    "Object Label,Object API Name,Object Description,Version Introduced,Version Deleted\r\n"
                ),
                call("Test,test__Test__c,Description,Project 1.1,\r\n"),
                call(
                    "Object API Name,Field Label,Field API Name,Type,Help Text,Field Description,Allowed Values,Length,Version Introduced,Version Allowed Values Last Changed,Version Help Text Last Changed,Version Deleted\r\n"
                ),
                call(
                    "test__Test__c,Type,test__Type__c,Text,Type of field.,,,255,Project 1.1,,,\r\n"
                ),
            ],
            any_order=True,
        )

    def test_init_options__defaults(self):
        project_config = create_project_config()
        project_config.project__name = "Project"

        task = create_task(
            GenerateDataDictionary, {"release_prefix": "rel/"}, project_config
        )

        assert task.options["object_path"] == "Project Objects.csv"
        assert task.options["field_path"] == "Project Fields.csv"

    def test_init_options(self):
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "objects.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        assert task.options["object_path"] == "objects.csv"
        assert task.options["field_path"] == "fields.csv"
