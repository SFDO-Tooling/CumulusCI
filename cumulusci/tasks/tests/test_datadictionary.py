import os
import unittest
import xml.etree.ElementTree as ET

from unittest.mock import Mock, call, patch

from cumulusci.tasks.datadictionary import GenerateDataDictionary
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tests.util import create_project_config
from distutils.version import LooseVersion


class test_GenerateDataDictionary(unittest.TestCase):
    def test_set_version_with_props(self):
        task = create_task(GenerateDataDictionary)

        this_dict = {"version": LooseVersion("1.1"), "test": "test"}
        task._set_version_with_props(this_dict, {"version": None, "test": "bad"})

        assert this_dict["version"] == LooseVersion("1.1")
        assert this_dict["test"] == "test"

        this_dict = {"version": LooseVersion("1.1"), "test": "test"}
        task._set_version_with_props(this_dict, {"version": "1.2", "test": "good"})

        assert this_dict["version"] == LooseVersion("1.1")
        assert this_dict["test"] == "good"

        this_dict = {"version": LooseVersion("1.3"), "test": "test"}
        task._set_version_with_props(this_dict, {"version": "1.2", "test": "bad"})

        assert this_dict["version"] == LooseVersion("1.2")
        assert this_dict["test"] == "test"

    def test_version_from_tag_name(self):
        task = create_task(GenerateDataDictionary)
        project_config = create_project_config("TestRepo", "TestOwner")
        project_config.project__package__git__prefix_release = "release/"

        assert task._version_from_tag_name("release/1.1") == LooseVersion("1.1")

    def test_write_results(self):
        task = create_task(
            GenerateDataDictionary,
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )

        task.schema = {
            "Account": {
                "fields": {
                    "Test__c": {
                        "version": LooseVersion("1.1"),
                        "label": "Test",
                        "help_text": "Text field",
                        "picklist_values": "",
                    }
                }
            },
            "Child__c": {
                "fields": {
                    "Parent__c": {
                        "version": LooseVersion("1.2"),
                        "label": "Parent",
                        "help_text": "Lookup",
                        "picklist_values": "",
                    }
                },
                "version": LooseVersion("1.0"),
                "label": "Child",
                "help_text": "Child object",
            },
        }
        task._write_results()
        # FIXME: mock and assert

    def test_process_field_element__new(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account__c</fullName>
    <label>Account</label>
    <type>Lookup</type>
</CustomField>
"""
        task = create_task(
            GenerateDataDictionary,
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )

        task._init_schema()
        task._process_field_element("Test__c", ET.fromstring(xml_source), "1.1")

        assert "Test__c" in task.schema
        assert "Account__c" in task.schema["Test__c"]["fields"]
        assert task.schema["Test__c"]["fields"]["Account__c"] == {
            "version": LooseVersion("1.1"),
            "help_text": "",
            "label": "Account",
            "picklist_values": "",
        }

    def test_process_field_element__standard(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account</fullName>
    <label>Account</label>
    <type>Lookup</type>
</CustomField>
"""
        task = create_task(
            GenerateDataDictionary,
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )

        task._init_schema()
        task._process_field_element("Test__c", ET.fromstring(xml_source), "1.1")

        assert task.schema["Test__c"]["fields"]["Account"]["version"] is None

    def test_process_field_element__updated(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>Account__c</fullName>
    <inlineHelpText>{}</inlineHelpText>
    <label>Account</label>
    <type>Lookup</type>
</CustomField>
"""
        task = create_task(
            GenerateDataDictionary,
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )

        task._init_schema()
        task._process_field_element(
            "Test__c", ET.fromstring(xml_source.format("Initial")), "1.1"
        )

        assert task.schema["Test__c"]["fields"]["Account__c"] == {
            "version": LooseVersion("1.1"),
            "help_text": "Initial",
            "label": "Account",
            "picklist_values": "",
        }

        task._process_field_element(
            "Test__c", ET.fromstring(xml_source.format("New")), "1.2"
        )
        assert task.schema["Test__c"]["fields"]["Account__c"] == {
            "version": LooseVersion("1.1"),
            "help_text": "New",
            "label": "Account",
            "picklist_values": "",
        }

    def test_process_field_element__picklist_values(self):
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
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )

        task._init_schema()
        task._process_field_element("Test__c", ET.fromstring(xml_source), "1.1")

        assert task.schema["Test__c"]["fields"]["Type__c"] == {
            "version": LooseVersion("1.1"),
            "help_text": "",
            "label": "Type",
            "picklist_values": "Test 1; Test 2",
        }

    def test_process_object_element(self):
        xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description</description>
    <label>Test</label>
    <fields>
        <fullName>Type__c</fullName>
        <inlineHelpText>Type of field.</inlineHelpText>
        <label>Type</label>
        <type>Text</type>
    </fields>
</CustomObject>"""

        task = create_task(
            GenerateDataDictionary,
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )

        task._init_schema()
        task._process_object_element(
            "Test__c", ET.fromstring(xml_source), LooseVersion("1.1")
        )

        assert task.schema == {
            "Test__c": {
                "label": "Test",
                "version": LooseVersion("1.1"),
                "help_text": "Description",
                "fields": {
                    "Type__c": {
                        "version": LooseVersion("1.1"),
                        "label": "Type",
                        "help_text": "Type of field.",
                        "picklist_values": "",
                    }
                },
            }
        }

        def test_process_object_element__standard(self):
            xml_source = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Description</description>
    <label>Test</label>
</CustomObject>"""

            task = create_task(
                GenerateDataDictionary,
                {"object_path": "object.csv", "field_path": "fields.csv"},
            )

            task._init_schema()
            task._process_object_element(
                "Account", ET.fromstring(xml_source), LooseVersion("1.1")
            )

            assert task.schema["Account"]["version"] is None

    @patch("cumulusci.tasks.datadictionary.ET.fromstring")
    def test_process_sfdx_release(self, fromstring):
        task = create_task(
            GenerateDataDictionary,
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )

        task.name_list = [
            "force-app/main/default/objects/Child__c.object-meta.xml",
            "force-app/main/default/objects/Child__c/fields/Lookup__c.field-meta.xml",
            "force-app/main/default/objects/Parent__c.object-meta.xml",
            ".gitignore",
            "test__c.object-meta.xml",
        ]
        task.zip_prefix = "ZIPPREFIX"

        zip_file = Mock()
        zip_file.read.return_value = "<test></test>"
        task._process_object_element = Mock()
        task._process_field_element = Mock()
        task._process_sfdx_release(zip_file, LooseVersion("1.1"))

        zip_file.read.assert_has_calls(
            [
                call(
                    os.path.join(
                        os.path.sep,
                        task.zip_prefix,
                        "force-app/main/default/objects/Child__c.object-meta.xml",
                    ).strip(os.path.sep)
                ),
                call(
                    os.path.join(
                        os.path.sep,
                        task.zip_prefix,
                        "force-app/main/default/objects/Child__c/fields/Lookup__c.field-meta.xml",
                    ).strip(os.path.sep)
                ),
                call(
                    os.path.join(
                        os.path.sep,
                        task.zip_prefix,
                        "force-app/main/default/objects/Parent__c.object-meta.xml",
                    ).strip(os.path.sep)
                ),
            ]
        )

        task._process_object_element.assert_has_calls(
            [
                call("Child__c", ET.fromstring("<test></test>"), LooseVersion("1.1")),
                call("Parent__c", ET.fromstring("<test></test>"), LooseVersion("1.1")),
            ]
        )
        task._process_field_element.assert_has_calls(
            [call("Child__c", ET.fromstring("<test></test>"), LooseVersion("1.1"))]
        )

    @patch("cumulusci.tasks.datadictionary.ET.fromstring")
    def test_process_mdapi_release(self, fromstring):
        task = create_task(
            GenerateDataDictionary,
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )

        task.name_list = [
            "src/objects/Child__c.object",
            "src/objects/Parent__c.object",
            ".gitignore",
            "test__c.object",
        ]
        task.zip_prefix = "ZIPPREFIX"

        zip_file = Mock()
        zip_file.read.return_value = "<test></test>"
        task._process_object_element = Mock()
        task._process_mdapi_release(zip_file, LooseVersion("1.1"))

        zip_file.read.assert_has_calls(
            [
                call(
                    os.path.join(
                        os.path.sep, task.zip_prefix, "src/objects/Child__c.object"
                    ).strip(os.path.sep)
                ),
                call(
                    os.path.join(
                        os.path.sep, task.zip_prefix, "src/objects/Parent__c.object"
                    ).strip(os.path.sep)
                ),
            ]
        )

        task._process_object_element.assert_has_calls(
            [
                call("Child__c", ET.fromstring("<test></test>"), LooseVersion("1.1")),
                call("Parent__c", ET.fromstring("<test></test>"), LooseVersion("1.1")),
            ]
        )

    @patch("zipfile.ZipFile")
    def test_walk_releases__mdapi(self, zip_file):
        task = create_task(
            GenerateDataDictionary,
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )
        task.project_config.project__git__prefix_release = "rel/"

        task.get_repo = Mock()
        release = Mock()
        release.draft = False
        release.prerelease = False
        release.tag_name = "rel/1.1"
        task.get_repo.return_value.releases.return_value = [release]
        task._process_mdapi_release = Mock()
        zip_file.return_value.namelist.return_value = ["PREFIX/src/objects"]

        task._walk_releases()

        task._process_mdapi_release.assert_called_once_with(
            zip_file.return_value, "1.1"
        )

    @patch("zipfile.ZipFile")
    def test_walk_releases__sfdx(self, zip_file):
        task = create_task(
            GenerateDataDictionary,
            {"object_path": "object.csv", "field_path": "fields.csv"},
        )
        task.project_config.project__git__prefix_release = "rel/"

        task.get_repo = Mock()
        release = Mock()
        release.draft = False
        release.prerelease = False
        release.tag_name = "rel/1.1"
        task.get_repo.return_value.releases.return_value = [release]
        task._process_sfdx_release = Mock()
        zip_file.return_value.namelist.return_value = [
            "PREFIX/force-app/main/default/objects"
        ]

        task._walk_releases()

        task._process_sfdx_release.assert_called_once_with(zip_file.return_value, "1.1")

    def test_init_schema(self):
        task = create_task(GenerateDataDictionary, {})
        task._init_schema()

        assert task.schema is not None

    def test_run_task(self):
        pass  # FIXME

    def test_init_options__defaults(self):
        task = create_task(GenerateDataDictionary, {})

        task._init_options({})

        assert task.options["object_path"] == "sObject Data Dictionary.csv"
        assert task.options["field_path"] == "Field Data Dictionary.csv"

    def test_init_options(self):
        task = create_task(GenerateDataDictionary, {})

        task._init_options({"object_path": "objects.csv", "field_path": "fields.csv"})

        assert task.options["object_path"] == "objects.csv"
        assert task.options["field_path"] == "fields.csv"
