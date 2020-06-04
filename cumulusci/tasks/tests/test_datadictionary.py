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
from cumulusci.core.exceptions import DependencyResolutionError, TaskOptionsError


class test_GenerateDataDictionary(unittest.TestCase):
    def test_version_from_tag_name(self):
        task = create_task(GenerateDataDictionary, {})

        assert task._version_from_tag_name("release/1.1", "release/") == StrictVersion(
            "1.1"
        )

    def test_write_object_results(self):
        task = create_task(GenerateDataDictionary, {})

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

        assert (
            result
            == "Object Label,Object API Name,Object Description,Version Introduced,Version Deleted\r\nTest,test__Test__c,Description,Test 1.1,Test 1.2\r\n"
        )

    def test_write_field_results(self):
        task = create_task(GenerateDataDictionary, {})

        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))
        v2 = PackageVersion(p, StrictVersion("1.2"))
        task.package_versions = {p: [v2.version, v.version]}
        task.omit_sobjects = set()
        task.sobjects = {
            "test__Test__c": [
                SObjectDetail(v, "test__Test__c", "Test Object", "Desc"),
                SObjectDetail(v2, "test__Test__c", "Test Object", "Desc"),
            ]
        }
        task.fields = {
            "Account.test__Desc__c": [
                FieldDetail(v2, "Account", "test__Desc__c", "Desc", "Text", "", "", "")
            ],
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
                )
            ],
        }

        f = io.StringIO()
        task._write_field_results(f)
        f.seek(0)
        result = f.read()

        assert result == (
            "Object Label,Object API Name,Field Label,Field API Name,Type,Picklist Values,Help Text,Field Description,Version Introduced,Version Picklist Values Last Changed,Version Help Text Last Changed,Version Deleted\r\n"
            "Account,Account,Desc,test__Desc__c,Text,,,,Test 1.2,,,\r\n"
            "Test Object,test__Test__c,Type,test__Type__c,Picklist,Foo; Bar; New Value,New Help,Description,Test 1.1,Test 1.2,Test 1.2,\r\n"
            "Test Object,test__Test__c,Account,test__Account__c,Lookup to Account,,Help,Description,Test 1.1,,,Test 1.2\r\n"
        )

    def test_write_field_results__omit_sobjects(self):
        task = create_task(GenerateDataDictionary, {})

        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))
        v2 = PackageVersion(p, StrictVersion("1.2"))
        task.package_versions = {p: [v2.version, v.version]}
        task.omit_sobjects = set(["test__Test2__c"])
        task.sobjects = {
            "test__Test__c": [
                SObjectDetail(v, "test__Test__c", "Test Object", "Desc"),
                SObjectDetail(v2, "test__Test__c", "Test Object", "Desc"),
            ]
        }
        task.fields = {
            "test__Test2__c.test__Blah__c": [
                FieldDetail(
                    v,
                    "test__Test2__c",
                    "test__Blah__c",
                    "Test Field",
                    "Text",
                    "Help",
                    "Description",
                    "",
                )
            ],
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
                )
            ],
        }

        f = io.StringIO()
        task._write_field_results(f)
        f.seek(0)
        result = f.read()

        assert result == (
            "Object Label,Object API Name,Field Label,Field API Name,Type,Picklist Values,Help Text,Field Description,Version Introduced,Version Picklist Values Last Changed,Version Help Text Last Changed,Version Deleted\r\n"
            "Test Object,test__Test__c,Type,test__Type__c,Picklist,Foo; Bar; New Value,New Help,Description,Test 1.1,Test 1.2,Test 1.2,\r\n"
            "Test Object,test__Test__c,Account,test__Account__c,Lookup to Account,,Help,Description,Test 1.1,,,Test 1.2\r\n"
        )

    def test_should_process_object(self):
        object_source_negative = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <customSettingsType>Hierarchy</customSettingsType>
    <description>Description</description>
    <label>Test</label>
</CustomObject>"""

        object_source_positive = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description</description>
    <label>Test</label>
</CustomObject>"""

        task = create_task(GenerateDataDictionary, {})

        assert task._should_process_object(
            "test__", "test__Obj__c", metadata_tree.fromstring(object_source_positive)
        )
        assert task._should_process_object("test__", "test__Obj__c", None)
        assert not task._should_process_object(
            "test__", "test__Obj__e", metadata_tree.fromstring(object_source_positive)
        )
        assert not task._should_process_object(
            "test__", "test__Obj__c", metadata_tree.fromstring(object_source_negative)
        )
        assert not task._should_process_object(
            "test__", "foo__Obj__c", metadata_tree.fromstring(object_source_positive)
        )
        assert not task._should_process_object(
            "test__", "Account", metadata_tree.fromstring(object_source_positive)
        )

    def test_should_process_object_fields(self):
        object_source_negative = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <customSettingsType>Hierarchy</customSettingsType>
    <description>Description</description>
    <label>Test</label>
</CustomObject>"""

        object_source_positive = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description</description>
    <label>Test</label>
</CustomObject>"""

        task = create_task(GenerateDataDictionary, {})

        assert task._should_process_object_fields(
            "test__Obj__c", metadata_tree.fromstring(object_source_positive)
        )
        assert task._should_process_object_fields("test__Obj__c", None)
        assert task._should_process_object_fields(
            "Account", metadata_tree.fromstring(object_source_positive)
        )
        assert not task._should_process_object_fields(
            "test__Obj__e", metadata_tree.fromstring(object_source_positive)
        )
        assert not task._should_process_object_fields(
            "test__Obj__c", metadata_tree.fromstring(object_source_negative)
        )

    def test_process_field_element__new(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Lookup__c</fullName>
    <label>Test</label>
    <type>Lookup</type>
    <referenceTo>Test__c</referenceTo>
</CustomField>
"""
        task = create_task(GenerateDataDictionary, {})
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        task._init_schema()
        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "test__Test__c.test__Lookup__c" in task.fields

        assert task.fields["test__Test__c.test__Lookup__c"] == [
            FieldDetail(
                v,
                "test__Test__c",
                "test__Lookup__c",
                "Test",
                "Lookup to test__Test__c",
                "",
                "",
                "",
            )
        ]

    def test_process_field_element__master_detail(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Lookup__c</fullName>
    <label>Test</label>
    <type>MasterDetail</type>
    <referenceTo>Test__c</referenceTo>
</CustomField>
"""
        task = create_task(GenerateDataDictionary, {})
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        task._init_schema()
        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "test__Test__c.test__Lookup__c" in task.fields
        assert task.fields["test__Test__c.test__Lookup__c"] == [
            FieldDetail(
                v,
                "test__Test__c",
                "test__Lookup__c",
                "Test",
                "Master-Detail Relationship to test__Test__c",
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
        task = create_task(GenerateDataDictionary, {})

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
        task = create_task(GenerateDataDictionary, {})

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
        task = create_task(GenerateDataDictionary, {})

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
        task = create_task(GenerateDataDictionary, {})

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
        task = create_task(GenerateDataDictionary, {})

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
            )
        ]

    def test_process_field_element__text_length(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Type__c</fullName>
    <label>Type</label>
    <type>Text</type>
    <length>128</length>
</CustomField>
"""
        task = create_task(GenerateDataDictionary, {})

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.fields["test__Test__c.test__Type__c"] == [
            FieldDetail(
                v, "test__Test__c", "test__Type__c", "Type", "Text (128)", "", "", ""
            )
        ]

    def test_process_field_element__number_length(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Type__c</fullName>
    <label>Type</label>
    <type>Number</type>
    <precision>18</precision>
    <scale>2</scale>
</CustomField>
"""
        task = create_task(GenerateDataDictionary, {})

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.fields["test__Test__c.test__Type__c"] == [
            FieldDetail(
                v, "test__Test__c", "test__Type__c", "Type", "Number (16.2)", "", "", ""
            )
        ]

    def test_process_object_element(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description</description>
    <label>Test Object</label>
    <fields>
        <fullName>Type__c</fullName>
        <inlineHelpText>Type of field.</inlineHelpText>
        <description>Desc</description>
        <label>Type</label>
        <type>Text</type>
        <length>128</length>
    </fields>
</CustomObject>"""

        task = create_task(GenerateDataDictionary, {})

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))
        task._process_object_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.sobjects == {
            "test__Test__c": [
                SObjectDetail(v, "test__Test__c", "Test Object", "Description")
            ]
        }
        assert task.fields == {
            "test__Test__c.test__Type__c": [
                FieldDetail(
                    v,
                    "test__Test__c",
                    "test__Type__c",
                    "Type",
                    "Text (128)",
                    "Type of field.",
                    "Desc",
                    "",
                )
            ]
        }

    def test_process_object_element__standard(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
<description>Description</description>
<label>Test</label>
</CustomObject>"""

        task = create_task(GenerateDataDictionary, {})

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))
        task._process_object_element(
            "Account", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "Account" not in task.sobjects

    def test_process_object_element__custom_setting(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
<customSettingsType>List</customSettingsType>
<description>Description</description>
<label>Test</label>
</CustomObject>"""

        task = create_task(GenerateDataDictionary, {})

        task._init_schema()
        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))
        task._process_object_element(
            "test__CS__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "test__CS__c" not in task.sobjects
        assert task.omit_sobjects == set(["test__CS__c"])

    def test_process_sfdx_release(self):
        object_source = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description</description>
    <label>Test</label>
</CustomObject>"""
        field_source = b"""<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
        <fullName>Type__c</fullName>
        <label>Type</label>
        <type>Text</type>
        <length>128</length>
    </CustomField>
"""

        def zip_read(filename):
            if filename.endswith(".object-meta.xml"):
                return object_source

            return field_source

        task = create_task(GenerateDataDictionary, {})

        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        zip_file = Mock()
        zip_file.read.side_effect = zip_read
        zip_file.namelist.return_value = [
            "force-app/main/default/objects/Child__c/Child__c.object-meta.xml",
            "force-app/main/default/objects/Child__c/fields/Lookup__c.field-meta.xml",
            "force-app/main/default/objects/Parent__c/Parent__c.object-meta.xml",
            ".gitignore",
            "test__c.object-meta.xml",
        ]
        task._process_object_element = Mock()
        task._process_field_element = Mock()
        task._process_sfdx_release(zip_file, v)

        zip_file.read.assert_has_calls(
            [
                call(
                    "force-app/main/default/objects/Child__c/Child__c.object-meta.xml"
                ),
                call(
                    "force-app/main/default/objects/Child__c/Child__c.object-meta.xml"
                ),
                call(
                    "force-app/main/default/objects/Child__c/fields/Lookup__c.field-meta.xml"
                ),
                call(
                    "force-app/main/default/objects/Parent__c/Parent__c.object-meta.xml"
                ),
            ]
        )

        assert len(task._process_object_element.call_args_list) == 2
        assert task._process_object_element.call_args_list[0][0][0] == "test__Child__c"
        assert task._process_object_element.call_args_list[1][0][0] == "test__Parent__c"

        assert len(task._process_field_element.call_args_list) == 1
        assert task._process_object_element.call_args_list[0][0][0] == "test__Child__c"

    def test_process_sfdx_release__skips_custom_settings_fields(self):
        object_source = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <customSettingsType>Hierarchy</customSettingsType>
    <description>Description</description>
    <label>Test</label>
</CustomObject>"""
        field_source = b"""<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
        <fullName>Type__c</fullName>
        <label>Type</label>
        <type>Text</type>
        <length>128</length>
    </CustomField>
"""

        def zip_read(filename):
            if filename.endswith(".object-meta.xml"):
                return object_source

            return field_source

        task = create_task(GenerateDataDictionary, {})
        task._init_schema()

        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        zip_file = Mock()
        zip_file.read.side_effect = zip_read
        zip_file.namelist.return_value = [
            "force-app/main/default/objects/Child__c/Child__c.object-meta.xml",
            "force-app/main/default/objects/Child__c/fields/Lookup__c.field-meta.xml",
            "force-app/main/default/objects/Parent__c/Parent__c.object-meta.xml",
            ".gitignore",
            "test__c.object-meta.xml",
        ]
        task._process_object_element = Mock()
        task._process_field_element = Mock()
        task._process_sfdx_release(zip_file, v)

        task._process_field_element.assert_not_called()

        zip_file.read.assert_has_calls(
            [
                call(
                    "force-app/main/default/objects/Child__c/Child__c.object-meta.xml"
                ),
                call(
                    "force-app/main/default/objects/Child__c/Child__c.object-meta.xml"
                ),
                call(
                    "force-app/main/default/objects/Parent__c/Parent__c.object-meta.xml"
                ),
            ]
        )
        assert task.omit_sobjects == set(["test__Child__c", "test__Parent__c"])

    def test_process_sfdx_release__handles_object_not_found(self):
        field_source = b"""<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
        <fullName>Type__c</fullName>
        <label>Type</label>
        <type>Text</type>
        <length>128</length>
    </CustomField>
"""

        def zip_read(filename):
            return field_source

        task = create_task(GenerateDataDictionary, {})
        task._init_schema()

        p = Package(None, "Test", "test__", "rel/")
        v = PackageVersion(p, StrictVersion("1.1"))

        zip_file = Mock()
        zip_file.read.side_effect = zip_read
        zip_file.namelist.return_value = [
            "force-app/main/default/objects/Child__c/fields/Lookup__c.field-meta.xml"
        ]
        task._process_object_element = Mock()
        task._process_field_element = Mock()
        task._should_process_object_fields = Mock(return_value=True)

        task._process_sfdx_release(zip_file, v)

        task._should_process_object_fields.assert_called_once_with(
            "test__Child__c", None
        )

    @patch("cumulusci.tasks.datadictionary.download_extract_github_from_repo")
    def test_walk_releases__mdapi(self, extract_github):
        project_config = create_project_config()
        project_config.project__git__prefix_release = "rel/"
        project_config.project__name = "Project"
        task = create_task(GenerateDataDictionary, {}, project_config=project_config)
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

        task = create_task(GenerateDataDictionary, {}, project_config=project_config)
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

    @patch("cumulusci.tasks.datadictionary.download_extract_github_from_repo")
    def test_walk_releases__draft(self, extract_github):
        project_config = create_project_config()
        project_config.project__git__prefix_release = "rel/"
        project_config.project__name = "Project"
        task = create_task(GenerateDataDictionary, {}, project_config=project_config)
        task._init_schema()

        repo = Mock()
        release_draft = Mock()
        release_draft.draft = False
        release_draft.prerelease = True
        release_draft.tag_name = "rel/1.1_Beta_1"
        release_real = Mock()
        release_real.draft = False
        release_real.prerelease = False
        release_real.tag_name = "rel/1.1"

        repo.releases.return_value = [release_draft, release_real]
        task._process_mdapi_release = Mock()
        extract_github.return_value.namelist.return_value = ["src/objects/"]
        p = Package(repo, "Test", "test__", "rel/")

        task._walk_releases(p)

        task._process_mdapi_release.assert_called_once()

    def test_init_schema(self):
        task = create_task(GenerateDataDictionary, {})
        task._init_schema()

        assert task.fields is not None
        assert task.sobjects is not None

    def test_run_task__additional_dependencies(self):
        project_config = create_project_config()
        project_config.keychain.get_service = Mock()
        project_config.project__package__name = "Project"
        project_config.project__name = "Project"
        project_config.project__package__namespace = "test"
        project_config.project__dependencies = [{"github": "http://example"}]

        task = create_task(
            GenerateDataDictionary,
            {"additional_dependencies": [{"github": "http://test"}]},
            project_config=project_config,
        )
        task.get_repo = Mock()
        release = Mock()
        release.draft = False
        release.prerelease = False
        release.tag_name = "release/1.1"
        task.get_repo.return_value.releases.return_value = [release]
        task._get_repo_dependencies = Mock(return_value=[1, 2])
        task._walk_releases = Mock()

        task._run_task()

        task._get_repo_dependencies.assert_has_calls(
            [
                call([{"github": "http://test"}], include_beta=False),
                call(project_config.project__dependencies, include_beta=False),
            ]
        )

        task._walk_releases.assert_has_calls(
            [
                call(
                    Package(
                        task.get_repo.return_value,
                        project_config.project__package__name,
                        "test__",
                        "release/",
                    )
                ),
                call(1),
                call(2),
                call(1),
                call(2),
            ]
        )

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

        m.return_value.write.assert_has_calls(
            [
                call(
                    "Object Label,Object API Name,Object Description,Version Introduced,Version Deleted\r\n"
                ),
                call("Test,test__Test__c,Description,Project 1.1,\r\n"),
                call(
                    "Object Label,Object API Name,Field Label,Field API Name,Type,Picklist Values,Help Text,Field Description,Version Introduced,Version Picklist Values Last Changed,Version Help Text Last Changed,Version Deleted\r\n"
                ),
                call(
                    "Test,test__Test__c,Type,test__Type__c,Text (255),,Type of field.,,Project 1.1,,,\r\n"
                ),
            ],
            any_order=True,
        )

    def test_init_options(self):
        task = create_task(
            GenerateDataDictionary,
            {"object_path": "objects.csv", "field_path": "fields.csv"},
        )

        assert task.options["object_path"] == "objects.csv"
        assert task.options["field_path"] == "fields.csv"

    def test_init_options__defaults(self):
        project_config = create_project_config()
        project_config.project__name = "Project"

        task = create_task(GenerateDataDictionary, {}, project_config)

        assert task.options["object_path"] == "Project Objects.csv"
        assert task.options["field_path"] == "Project Fields.csv"

    def test_init_options__bad_deps(self):
        project_config = create_project_config()
        project_config.project__name = "Project"

        with self.assertRaises(TaskOptionsError):
            create_task(
                GenerateDataDictionary,
                {"additional_dependencies": [{"namespace": "foo"}]},
                project_config,
            )

    def test_get_repo_dependencies__none(self):
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        assert task._get_repo_dependencies([]) == []

    def test_get_repo_dependencies__cannot_get_repo(self):
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

        project_config.project__dependencies = [{"github": "test"}]
        project_config.get_repo_from_url = Mock(return_value=None)

        with self.assertRaises(DependencyResolutionError):
            task._get_repo_dependencies(project_config.project__dependencies)

    def test_get_repo_dependencies__success(self):
        project_config = create_project_config()
        project_config.project__git__prefix_release = "rel/"
        project_config.project__name = "Project"

        task = create_task(GenerateDataDictionary, {}, project_config=project_config)

        project_config.project__dependencies = [{"github": "test"}]
        first_repo = Mock()
        second_repo = Mock()
        project_config.get_repo_from_url = Mock(
            side_effect=[first_repo, second_repo, first_repo]
        )
        project_config.get_ref_for_dependency = Mock(return_value=(Mock(), Mock()))

        first_repo.owner = "Test"
        first_repo.name = "Repo1"
        second_repo.owner = "Test"
        second_repo.name = "Repo2"

        cumulusci_yml_one = b"""
project:
    name: Test 1
    package:
        name: Test 1
        namespace: test1
    dependencies:
        - github: "test2"
"""
        cumulusci_yml_two = b"""
project:
    name: Test 2
    dependencies:
        - github: "test1"
    git:
        prefix_release: "rel/"
"""

        first_repo.file_contents.return_value.decoded = cumulusci_yml_one
        second_repo.file_contents.return_value.decoded = cumulusci_yml_two

        assert task._get_repo_dependencies(project_config.project__dependencies) == [
            Package(first_repo, "Test 1", "test1__", "release/"),
            Package(second_repo, "Test/Repo2", "", "rel/"),
        ]
