import io
from collections import defaultdict
from unittest.mock import Mock, call, mock_open, patch

import pytest

from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.dependencies import (
    GitHubDynamicDependency,
    parse_dependencies,
)
from cumulusci.core.exceptions import (
    DependencyParseError,
    DependencyResolutionError,
    TaskOptionsError,
)
from cumulusci.tasks.datadictionary import (
    PRERELEASE_SIGIL,
    FieldDetail,
    GenerateDataDictionary,
    Package,
    PackageVersion,
    SObjectDetail,
)
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tests.util import create_project_config
from cumulusci.utils import temporary_dir
from cumulusci.utils.version_strings import LooseVersion
from cumulusci.utils.xml import metadata_tree
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load


class TestGenerateDataDictionary:
    def test_version_from_tag_name(self):
        task = create_task(GenerateDataDictionary, {})

        assert task._version_from_tag_name("release/1.1", "release/") == LooseVersion(
            "1.1"
        )

    def test_write_object_results(self):
        task = create_task(GenerateDataDictionary, {})

        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))
        v2 = PackageVersion(package=p, version=LooseVersion("1.2"))
        task.package_versions = defaultdict(list)
        task.package_versions[p] = [v2.version, v.version]
        task.sobjects = defaultdict(list)
        task.sobjects["test__Test__c"] = [
            SObjectDetail(
                version=v,
                api_name="test__Test__c",
                label="Test",
                description="Description",
            )
        ]

        f = io.StringIO()
        task._write_object_results(f)

        f.seek(0)
        result = f.read()

        assert (
            result
            == '"Object Label","Object API Name","Object Description","Version Introduced","Version Deleted"\r\n"Test","test__Test__c","Description","Test 1.1","Test 1.2"\r\n'
        )

    def test_write_field_results(self):
        task = create_task(GenerateDataDictionary, {})

        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))
        v2 = PackageVersion(package=p, version=LooseVersion("1.2"))

        task._init_schema()
        task.package_versions[p] = [v2.version, v.version]
        task.sobjects["test__Test__c"] = [
            SObjectDetail(
                version=v,
                api_name="test__Test__c",
                label="Test Object",
                description="Desc",
            ),
            SObjectDetail(
                version=v2,
                api_name="test__Test__c",
                label="Test Object",
                description="Desc",
            ),
        ]

        task.fields.update(
            {
                "Account.test__Desc__c": [
                    FieldDetail(
                        version=v2,
                        sobject="Account",
                        api_name="test__Desc__c",
                        label="Desc",
                        type="Text",
                        help_text="",
                        description="",
                        valid_values="",
                    )
                ],
                "test__Test__c.test__Type__c": [
                    FieldDetail(
                        version=v,
                        sobject="test__Test__c",
                        api_name="test__Type__c",
                        label="Type",
                        type="Picklist",
                        help_text="Help",
                        description="Description",
                        valid_values="Foo; Bar",
                    ),
                    FieldDetail(
                        version=v2,
                        sobject="test__Test__c",
                        api_name="test__Type__c",
                        label="Type",
                        type="Picklist",
                        help_text="New Help",
                        description="Description",
                        valid_values="Foo; Bar; New Value",
                    ),
                ],
                "test__Test__c.test__Account__c": [
                    FieldDetail(
                        version=v,
                        sobject="test__Test__c",
                        api_name="test__Account__c",
                        label="Account",
                        type="Lookup to Account",
                        help_text="Help",
                        description="Description",
                        valid_values="",
                    )
                ],
            }
        )

        f = io.StringIO()
        task._write_field_results(f)
        f.seek(0)
        result = f.read()

        assert result == (
            '"Object Label","Object API Name","Field Label","Field API Name",'
            '"Type","Picklist Values","Help Text","Field Description","Version Introduced",'
            '"Version Picklist Values Last Changed","Version Help Text Last Changed",'
            '"Version Deleted"\r\n"Account","Account","Desc","test__Desc__c","Text",'
            '"","","","Test 1.2","","",""\r\n"Test Object","test__Test__c","Type",'
            '"test__Type__c","Picklist","Foo; Bar; New Value","New Help","Description",'
            '"Test 1.1","Test 1.2","Test 1.2",""\r\n"Test Object","test__Test__c",'
            '"Account","test__Account__c","Lookup to Account","","Help","Description",'
            '"Test 1.1","","","Test 1.2"\r\n'
        )

    def test_write_field_results__omit_sobjects(self):
        task = create_task(GenerateDataDictionary, {})

        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))
        v2 = PackageVersion(package=p, version=LooseVersion("1.2"))
        task._init_schema()
        task.package_versions[p] = [v2.version, v.version]
        task.omit_sobjects = set(["test__Test2__c"])
        task.sobjects["test__Test__c"] = [
            SObjectDetail(
                version=v,
                api_name="test__Test__c",
                label="Test Object",
                description="Desc",
            ),
            SObjectDetail(
                version=v2,
                api_name="test__Test__c",
                label="Test Object",
                description="Desc",
            ),
        ]
        task.fields["test__Test2__c.test__Blah__c"] = [
            FieldDetail(
                version=v,
                sobject="test__Test2__c",
                api_name="test__Blah__c",
                label="Test Field",
                type="Text",
                help_text="Help",
                description="Description",
                valid_values="",
            )
        ]
        task.fields["test__Test__c.test__Type__c"] = [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Type__c",
                label="Type",
                type="Picklist",
                help_text="Help",
                description="Description",
                valid_values="Foo; Bar",
            ),
            FieldDetail(
                version=v2,
                sobject="test__Test__c",
                api_name="test__Type__c",
                label="Type",
                type="Picklist",
                help_text="New Help",
                description="Description",
                valid_values="Foo; Bar; New Value",
            ),
        ]
        task.fields["test__Test__c.test__Account__c"] = [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Account__c",
                label="Account",
                type="Lookup to Account",
                help_text="Help",
                description="Description",
                valid_values="",
            )
        ]

        f = io.StringIO()
        task._write_field_results(f)
        f.seek(0)
        result = f.read()

        assert result == (
            '"Object Label","Object API Name","Field Label","Field API Name","Type",'
            '"Picklist Values","Help Text","Field Description","Version Introduced",'
            '"Version Picklist Values Last Changed","Version Help Text Last Changed",'
            '"Version Deleted"\r\n"Test Object","test__Test__c","Type","test__Type__c",'
            '"Picklist","Foo; Bar; New Value","New Help","Description","Test 1.1","Test 1.2",'
            '"Test 1.2",""\r\n"Test Object","test__Test__c","Account","test__Account__c",'
            '"Lookup to Account","","Help","Description","Test 1.1","","","Test 1.2"\r\n'
        )

    def test_should_process_object(self):
        object_source_negative = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description</description>
    <label>Test</label>
    <visibility>Protected</visibility>
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
        assert task._should_process_object(
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
    <visibility>Protected</visibility>
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
        assert task._should_process_object_fields(
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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._init_schema()
        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "test__Test__c.test__Lookup__c" in task.fields

        assert task.fields["test__Test__c.test__Lookup__c"] == [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Lookup__c",
                label="Test",
                type="Lookup to test__Test__c",
                description="",
                help_text="",
                valid_values="",
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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._init_schema()
        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "test__Test__c.test__Lookup__c" in task.fields
        assert task.fields["test__Test__c.test__Lookup__c"] == [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Lookup__c",
                label="Test",
                type="Master-Detail Relationship to test__Test__c",
                description="",
                help_text="",
                valid_values="",
            )
        ]

    def test_process_field_element__blank_elements(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Lookup__c</fullName>
    <label>Test</label>
    <description></description>
    <inlineHelpText></inlineHelpText>
    <type>MasterDetail</type>
    <referenceTo>Test__c</referenceTo>
</CustomField>
"""
        task = create_task(GenerateDataDictionary, {})
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._init_schema()
        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "test__Test__c.test__Lookup__c" in task.fields
        assert task.fields["test__Test__c.test__Lookup__c"] == [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Lookup__c",
                label="Test",
                type="Master-Detail Relationship to test__Test__c",
                description="",
                help_text="",
                valid_values="",
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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert len(task.fields) == 0

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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))
        v2 = PackageVersion(package=p, version=LooseVersion("1.2"))

        task._process_field_element(
            "test__Test__c",
            metadata_tree.fromstring(xml_source.format("Initial").encode("utf-8")),
            v,
        )

        assert task.fields["test__Test__c.test__Account__c"] == [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Account__c",
                label="Account",
                type="Lookup to Account",
                help_text="Initial",
                description="",
                valid_values="",
            )
        ]

        task._process_field_element(
            "test__Test__c",
            metadata_tree.fromstring(xml_source.format("New").encode("utf-8")),
            v2,
        )
        assert task.fields["test__Test__c.test__Account__c"] == [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Account__c",
                label="Account",
                type="Lookup to Account",
                help_text="Initial",
                description="",
                valid_values="",
            ),
            FieldDetail(
                version=v2,
                sobject="test__Test__c",
                api_name="test__Account__c",
                label="Account",
                type="Lookup to Account",
                help_text="New",
                description="",
                valid_values="",
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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.fields["test__Test__c.test__Type__c"] == [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Type__c",
                label="Type",
                type="Picklist",
                help_text="",
                description="",
                valid_values="Test 1; Test 2",
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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.fields["test__Test__c.test__Type__c"] == [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Type__c",
                label="Type",
                type="Picklist",
                help_text="",
                description="",
                valid_values="Test 1; Test 2",
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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.fields["test__Test__c.test__Type__c"] == [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Type__c",
                label="Type",
                type="Picklist",
                help_text="",
                description="",
                valid_values="Global Value Set Test Value Set",
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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.fields["test__Test__c.test__Type__c"] == [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Type__c",
                label="Type",
                type="Text (128)",
                help_text="",
                description="",
                valid_values="",
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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_field_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.fields["test__Test__c.test__Type__c"] == [
            FieldDetail(
                version=v,
                sobject="test__Test__c",
                api_name="test__Type__c",
                label="Type",
                type="Number (16.2)",
                help_text="",
                description="",
                valid_values="",
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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_object_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.sobjects == {
            "test__Test__c": [
                SObjectDetail(
                    version=v,
                    api_name="test__Test__c",
                    label="Test Object",
                    description="Description",
                )
            ]
        }
        assert task.fields == {
            "test__Test__c.test__Type__c": [
                FieldDetail(
                    version=v,
                    sobject="test__Test__c",
                    api_name="test__Type__c",
                    label="Type",
                    type="Text (128)",
                    help_text="Type of field.",
                    description="Desc",
                    valid_values="",
                )
            ]
        }

    def test_process_object_element__missing_description(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Test Object</label>
    <fields>
        <fullName>Type__c</fullName>
        <inlineHelpText>Type of field.</inlineHelpText>
        <label>Type</label>
        <type>Text</type>
        <length>128</length>
    </fields>
</CustomObject>"""

        task = create_task(GenerateDataDictionary, {})

        task._init_schema()
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_object_element(
            "test__Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert task.sobjects == {
            "test__Test__c": [
                SObjectDetail(
                    version=v,
                    api_name="test__Test__c",
                    label="Test Object",
                    description="",
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
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_object_element(
            "Account", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "Account" not in task.sobjects

    def test_process_object_element__protected_custom_setting(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
<customSettingsType>List</customSettingsType>
<description>Description</description>
<visibility>Protected</visibility>
<label>Test</label>
</CustomObject>"""

        task = create_task(GenerateDataDictionary, {})

        task._init_schema()
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_object_element(
            "test__CS__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "test__CS__c" not in task.sobjects
        assert task.omit_sobjects == set(["test__CS__c"])

    def test_process_object_element__protected_custom_setting_included(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
<customSettingsType>List</customSettingsType>
<description>Description</description>
<visibility>Protected</visibility>
<label>Test</label>
</CustomObject>"""

        task = create_task(GenerateDataDictionary, {"include_protected_schema": True})

        task._init_schema()
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        task._process_object_element(
            "test__CS__c", metadata_tree.fromstring(xml_source.encode("utf-8")), v
        )

        assert "test__CS__c" in task.sobjects
        assert "test__CS__c" not in task.omit_sobjects

    def test_process_object_element__protected_custom_setting_old(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
<customSettingsType>List</customSettingsType>
<description>Description</description>
<customSettingsVisibility>Protected</customSettingsVisibility>
<label>Test</label>
</CustomObject>"""

        task = create_task(GenerateDataDictionary, {})

        task._init_schema()
        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

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

        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

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

    def test_process_sfdx_release__skips_protected_custom_settings_fields(self):
        object_source = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <customSettingsType>Hierarchy</customSettingsType>
    <description>Description</description>
    <label>Test</label>
    <visibility>Protected</visibility>
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

        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        zip_file = Mock()
        zip_file.read.side_effect = zip_read
        zip_file.namelist.return_value = [
            "force-app/main/default/objects/Child__c/Child__c.object-meta.xml",
            "force-app/main/default/objects/Child__c/fields/Lookup__c.field-meta.xml",
            "force-app/main/default/objects/Parent__c/Parent__c.object-meta.xml",
            ".gitignore",
            "test__c.object-meta.xml",
            "sfdx-project.json",
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

        p = Package(
            repo=None, package_name="Test", namespace="test__", prefix_release="rel/"
        )
        v = PackageVersion(package=p, version=LooseVersion("1.1"))

        zip_file = Mock()
        zip_file.read.side_effect = zip_read
        zip_file.namelist.return_value = [
            "force-app/main/default/objects/Child__c/fields/Lookup__c.field-meta.xml",
            "sfdx-project.json",
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
        p = Package(
            repo=repo, package_name="Test", namespace="test__", prefix_release="rel/"
        )

        task._walk_releases(p)

        task._process_mdapi_release.assert_called_once_with(
            extract_github.return_value,
            PackageVersion(package=p, version=LooseVersion("1.1")),
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
            "force-app/main/default/objects/",
            "sfdx-project.json",
        ]
        p = Package(
            repo=repo, package_name="Test", namespace="test__", prefix_release="rel/"
        )

        task._walk_releases(p)

        task._process_sfdx_release.assert_called_once_with(
            extract_github.return_value,
            PackageVersion(package=p, version=LooseVersion("1.1")),
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
        release_draft.prerelease = False
        release_draft.tag_name = "uat/1.1_Beta_1"
        release_real = Mock()
        release_real.draft = False
        release_real.prerelease = False
        release_real.tag_name = "rel/1.1"

        repo.releases.return_value = [release_draft, release_real]
        task._process_zipfile = Mock()
        p = Package(
            repo=repo, package_name="Test", namespace="test__", prefix_release="rel/"
        )

        task._walk_releases(p)

        task._process_zipfile.assert_called_once()

    @patch("cumulusci.tasks.datadictionary.download_extract_github_from_repo")
    def test_walk_releases__prerelease(self, extract_github):
        project_config = create_project_config()
        project_config.project__git__prefix_release = "rel/"
        project_config.project__name = "Project"
        project_config.repo_info["branch"] = "feature/foo"
        task = create_task(
            GenerateDataDictionary,
            {"include_prerelease": True},
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
        p = Package(
            repo=repo, package_name="Test", namespace="test__", prefix_release="rel/"
        )

        task._walk_releases(p)

        extract_github.assert_has_calls(
            [call(repo, ref="rel/1.1"), call(repo, ref="feature/foo")], any_order=True
        )
        task._process_mdapi_release.assert_has_calls(
            [
                call(
                    extract_github.return_value,
                    PackageVersion(package=p, version=LooseVersion("1.1")),
                ),
                call(
                    extract_github.return_value,
                    PackageVersion(package=p, version=PRERELEASE_SIGIL),
                ),
            ]
        )

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
        project_config.project__dependencies = [
            {"github": "https://github.com/test/test"}
        ]

        task = create_task(
            GenerateDataDictionary,
            {"additional_dependencies": [{"github": "https://github.com/test/test"}]},
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

        with temporary_dir():
            task._run_task()

        task._get_repo_dependencies.assert_has_calls(
            [
                call(
                    [
                        GitHubDynamicDependency(github="https://github.com/test/test"),
                        GitHubDynamicDependency(github="https://github.com/test/test"),
                    ]
                ),
            ]
        )

        task._walk_releases.assert_has_calls(
            [
                call(
                    Package(
                        repo=task.get_repo.return_value,
                        package_name=project_config.project__package__name,
                        namespace="test__",
                        prefix_release="release/",
                    )
                ),
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
                    '"Object Label","Object API Name","Object Description","Version Introduced","Version Deleted"\r\n'
                ),
                call('"Test","test__Test__c","Description","Project 1.1",""\r\n'),
                call(
                    '"Object Label","Object API Name","Field Label","Field API Name","Type","Picklist Values","Help Text","Field Description","Version Introduced","Version Picklist Values Last Changed","Version Help Text Last Changed","Version Deleted"\r\n'
                ),
                call(
                    '"Test","test__Test__c","Type","test__Type__c","Text (255)","","Type of field.","","Project 1.1","","",""\r\n'
                ),
            ],
            any_order=True,
        )

    @patch("cumulusci.tasks.datadictionary.download_extract_github_from_repo")
    def test_run_task__prerelease(self, extract_github):
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
        xml_source_prerelease = """<?xml version="1.0" encoding="UTF-8"?>
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
    <fields>
        <fullName>Description__c</fullName>
        <inlineHelpText>Description of field.</inlineHelpText>
        <label>Description</label>
        <type>Text</type>
        <length>255</length>
    </fields>
</CustomObject>"""

        project_config = create_project_config()
        project_config.keychain.get_service = Mock()
        project_config.project__package__name = "Project"
        project_config.project__name = "Project"
        project_config.project__package__namespace = "test"
        project_config.repo_info["branch"] = "testbranch"

        task = create_task(
            GenerateDataDictionary,
            {"include_prerelease": True},
            project_config=project_config,
        )

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
        extract_github.return_value.read.side_effect = [
            xml_source.encode("utf-8"),
            xml_source_prerelease.encode("utf-8"),
        ]
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
                    '"Object Label","Object API Name","Object Description","Version Introduced","Version Deleted"\r\n'
                ),
                call('"Test","test__Test__c","Description","Project 1.1",""\r\n'),
                call(
                    '"Object Label","Object API Name","Field Label","Field API Name","Type","Picklist Values","Help Text","Field Description","Version Introduced","Version Picklist Values Last Changed","Version Help Text Last Changed","Version Deleted"\r\n'
                ),
                call(
                    '"Test","test__Test__c","Type","test__Type__c","Text (255)","","Type of field.","","Project 1.1","","",""\r\n'
                ),
                call(
                    '"Test","test__Test__c","Description","test__Description__c","Text (255)","","Description of field.","","Project Prerelease","","",""\r\n'
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

        with pytest.raises(DependencyParseError):
            create_task(
                GenerateDataDictionary,
                {"additional_dependencies": [{"namespace": "foo"}]},
                project_config,
            )

    def test_init_options__non_github_deps(self):
        project_config = create_project_config()
        project_config.project__name = "Project"

        with pytest.raises(TaskOptionsError):
            create_task(
                GenerateDataDictionary,
                {"additional_dependencies": [{"namespace": "foo", "version": "1.0"}]},
                project_config,
            )

    def test_init_options__prerelease(self):
        project_config = create_project_config()
        project_config.project__name = "Project"

        with pytest.raises(TaskOptionsError):
            create_task(
                GenerateDataDictionary,
                {
                    "include_prerelease": True,
                    "additional_dependencies": [
                        {"github": "http://github.com/test/test"}
                    ],
                },
                project_config,
            )

        task = create_task(
            GenerateDataDictionary,
            {"include_prerelease": True, "include_dependencies": True},
            project_config,
        )

        assert task.options["include_dependencies"] is False

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

        project_config.project__dependencies = [
            {"github": "https://github.com/test/test"}
        ]
        project_config.get_repo_from_url = Mock(return_value=None)

        with pytest.raises(DependencyResolutionError):
            task._get_repo_dependencies(
                parse_dependencies(project_config.project__dependencies)
            )

    @patch("cumulusci.tasks.datadictionary.get_static_dependencies")
    @patch("cumulusci.tasks.datadictionary.get_repo")
    @patch("cumulusci.tasks.datadictionary.get_remote_project_config")
    def test_get_repo_dependencies__success(
        self, get_remote_project_config, get_repo, get_static_dependencies
    ):
        project_config = create_project_config()
        project_config.project__git__prefix_release = "rel/"
        project_config.project__name = "Project"

        task = create_task(GenerateDataDictionary, {}, project_config=project_config)

        project_config.project__dependencies = [
            {"github": "https://github.com/test/test"}
        ]

        cumulusci_yml_one = io.StringIO(
            """
project:
    name: Test 1
    package:
        name: Test 1
        namespace: test1
    dependencies:
        - github: "https://github.com/test1/test1"
"""
        )
        cumulusci_yml_two = io.StringIO(
            """
project:
    name: Test 2
    package:
        name: Test 2
    dependencies:
        - github: "test1"
    git:
        prefix_release: "rel/"
"""
        )

        def fake_get_static_dependencies(
            context,
            dependencies=None,
            resolution_strategy=None,
            strategies=None,
            filter_function=None,
        ):
            filter_function(
                GitHubDynamicDependency(github="https://github.com/test/test")
            ),
            filter_function(
                GitHubDynamicDependency(github="https://github.com/test1/test1")
            )
            return [
                GitHubDynamicDependency(github="https://github.com/test/test"),
                GitHubDynamicDependency(github="https://github.com/test1/test1"),
            ]

        get_static_dependencies.side_effect = fake_get_static_dependencies

        get_remote_project_config.side_effect = [
            BaseProjectConfig(None, cci_safe_load(cumulusci_yml_one)),
            BaseProjectConfig(None, cci_safe_load(cumulusci_yml_two)),
        ]

        results = task._get_repo_dependencies(
            parse_dependencies(project_config.project__dependencies)
        )

        assert results == [
            Package(
                repo=get_repo.return_value,
                package_name="Test 1",
                namespace="test1__",
                prefix_release="release/",
            ),
            Package(
                repo=get_repo.return_value,
                package_name="Test 2",
                namespace="",
                prefix_release="rel/",
            ),
        ]
