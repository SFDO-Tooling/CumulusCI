import unittest

from unittest.mock import Mock, call, patch, mock_open

from cumulusci.tasks.datadictionary import GenerateDataDictionary
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tests.util import create_project_config
from cumulusci.utils.xml import metadata_tree
from distutils.version import LooseVersion


class test_GenerateDataDictionary(unittest.TestCase):
    def test_set_version_with_props(self):
        task = create_task(GenerateDataDictionary, {"release_prefix": "rel/"})

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
        task = create_task(GenerateDataDictionary, {"release_prefix": "release/"})

        assert task._version_from_tag_name("release/1.1") == LooseVersion("1.1")

    def test_write_results(self):
        task = create_task(
            GenerateDataDictionary,
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task.schema = {
            "Account": {
                "fields": {
                    "Test__c": {
                        "version": LooseVersion("1.1"),
                        "label": "Test",
                        "help_text": "Text field",
                        "picklist_values": "",
                        "type": "Text",
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
                        "type": "Lookup",
                    }
                },
                "version": LooseVersion("1.0"),
                "label": "Child",
                "help_text": "Child object",
            },
        }

        m = mock_open()
        with patch("builtins.open", m):
            task._write_results()

        m.assert_has_calls(
            [call("object.csv", "w"), call("fields.csv", "w")], any_order=True
        )
        m.return_value.write.assert_has_calls(
            [
                call(
                    "Object Name,Object Label,Object Description,Version Introduced\r\n"
                ),
                call("Child__c,Child,Child object,1.0\r\n"),
                call(
                    "Object Name,Field Name,Field Label,Type,Field Help Text,Picklist Values,Version Introduced\r\n"
                ),
                call("Account,Test__c,Test,Text,Text field,,1.1\r\n"),
                call("Child__c,Parent__c,Parent,Lookup,Lookup,,1.2\r\n"),
            ],
            any_order=True,
        )

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
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        task._process_field_element(
            "Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), "1.1"
        )

        assert "Test__c" in task.schema
        assert "Account__c" in task.schema["Test__c"]["fields"]
        assert task.schema["Test__c"]["fields"]["Account__c"] == {
            "version": LooseVersion("1.1"),
            "help_text": "",
            "label": "Account",
            "type": "Lookup",
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
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        task._process_field_element(
            "Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), "1.1"
        )

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
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        task._process_field_element(
            "Test__c",
            metadata_tree.fromstring(xml_source.format("Initial").encode("utf-8")),
            "1.1",
        )

        assert task.schema["Test__c"]["fields"]["Account__c"] == {
            "version": LooseVersion("1.1"),
            "help_text": "Initial",
            "label": "Account",
            "type": "Lookup",
            "picklist_values": "",
        }

        task._process_field_element(
            "Test__c",
            metadata_tree.fromstring(xml_source.format("New").encode("utf-8")),
            "1.2",
        )
        assert task.schema["Test__c"]["fields"]["Account__c"] == {
            "version": LooseVersion("1.1"),
            "help_text": "New",
            "label": "Account",
            "type": "Lookup",
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
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        task._process_field_element(
            "Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), "1.1"
        )

        assert task.schema["Test__c"]["fields"]["Type__c"] == {
            "version": LooseVersion("1.1"),
            "help_text": "",
            "label": "Type",
            "type": "Picklist",
            "picklist_values": "Test 1; Test 2",
        }

    def test_process_field_element__picklist_values_old_format(self):
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
        task._process_field_element(
            "Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), "1.1"
        )

        assert task.schema["Test__c"]["fields"]["Type__c"] == {
            "version": LooseVersion("1.1"),
            "help_text": "",
            "label": "Type",
            "type": "Picklist",
            "picklist_values": "Test 1; Test 2",
        }

    def test_process_field_element__picklist_values_global_value_set(self):
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
        task._process_field_element(
            "Test__c", metadata_tree.fromstring(xml_source.encode("utf-8")), "1.1"
        )

        assert task.schema["Test__c"]["fields"]["Type__c"] == {
            "version": LooseVersion("1.1"),
            "help_text": "",
            "label": "Type",
            "type": "Picklist",
            "picklist_values": "Global Value Set Test Value Set",
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
            {
                "object_path": "object.csv",
                "field_path": "fields.csv",
                "release_prefix": "rel/",
            },
        )

        task._init_schema()
        task._process_object_element(
            "Test__c",
            metadata_tree.fromstring(xml_source.encode("utf-8")),
            LooseVersion("1.1"),
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
                        "type": "Text",
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
                {
                    "object_path": "object.csv",
                    "field_path": "fields.csv",
                    "release_prefix": "rel/",
                },
            )

            task._init_schema()
            task._process_object_element(
                "Account",
                metadata_tree.fromstring(xml_source.encode("utf-8")),
                LooseVersion("1.1"),
            )

            assert task.schema["Account"]["version"] is None

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
        task._process_sfdx_release(zip_file, LooseVersion("1.1"))

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
                call(
                    "Child__c",
                    metadata_tree.fromstring("<test></test>"),
                    LooseVersion("1.1"),
                ),
                call(
                    "Parent__c",
                    metadata_tree.fromstring("<test></test>"),
                    LooseVersion("1.1"),
                ),
            ]
        )
        task._process_field_element.assert_has_calls(
            [
                call(
                    "Child__c",
                    metadata_tree.fromstring("<test></test>"),
                    LooseVersion("1.1"),
                )
            ]
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

        zip_file = Mock()
        zip_file.namelist.return_value = [
            "src/objects/Child__c.object",
            "src/objects/Parent__c.object",
            ".gitignore",
            "test__c.object",
        ]
        zip_file.read.return_value = "<test></test>"
        task._process_object_element = Mock()
        task._process_mdapi_release(zip_file, LooseVersion("1.1"))

        zip_file.read.assert_has_calls(
            [call("src/objects/Child__c.object"), call("src/objects/Parent__c.object")]
        )

        task._process_object_element.assert_has_calls(
            [
                call(
                    "Child__c",
                    metadata_tree.fromstring("<test></test>"),
                    LooseVersion("1.1"),
                ),
                call(
                    "Parent__c",
                    metadata_tree.fromstring("<test></test>"),
                    LooseVersion("1.1"),
                ),
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

        task.get_repo = Mock()
        release = Mock()
        release.draft = False
        release.prerelease = False
        release.tag_name = "rel/1.1"
        task.get_repo.return_value.releases.return_value = [release]
        task._process_mdapi_release = Mock()
        extract_github.return_value.namelist.return_value = ["src/objects/"]

        task._walk_releases()

        task._process_mdapi_release.assert_called_once_with(
            extract_github.return_value, "1.1"
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

        task.get_repo = Mock()
        release = Mock()
        release.draft = False
        release.prerelease = False
        release.tag_name = "rel/1.1"
        task.get_repo.return_value.releases.return_value = [release]
        task._process_sfdx_release = Mock()
        extract_github.return_value.namelist.return_value = [
            "force-app/main/default/objects/"
        ]

        task._walk_releases()

        task._process_sfdx_release.assert_called_once_with(
            extract_github.return_value, "1.1"
        )

    def test_init_schema(self):
        task = create_task(GenerateDataDictionary, {"release_prefix": "rel/"})
        task._init_schema()

        assert task.schema is not None

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
    </fields>
</CustomObject>"""
        project_config = create_project_config()
        project_config.keychain.get_service = Mock()
        project_config.project__name = "Project"

        task = create_task(
            GenerateDataDictionary,
            {"release_prefix": "rel/"},
            project_config=project_config,
        )

        task.get_repo = Mock()
        release = Mock()
        release.draft = False
        release.prerelease = False
        release.tag_name = "rel/1.1"
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
            [
                call("Project sObject Data Dictionary.csv", "w"),
                call("Project Field Data Dictionary.csv", "w"),
            ],
            any_order=True,
        )
        m.return_value.write.assert_has_calls(
            [
                call(
                    "Object Name,Object Label,Object Description,Version Introduced\r\n"
                ),
                call("Test__c,Test,Description,1.1\r\n"),
                call(
                    "Object Name,Field Name,Field Label,Type,Field Help Text,Picklist Values,Version Introduced\r\n"
                ),
                call("Test__c,Type__c,Type,Text,Type of field.,,1.1\r\n"),
            ],
            any_order=True,
        )

    def test_init_options__defaults(self):
        project_config = create_project_config()
        project_config.project__name = "Project"

        task = create_task(
            GenerateDataDictionary, {"release_prefix": "rel/"}, project_config
        )

        assert task.options["object_path"] == "Project sObject Data Dictionary.csv"
        assert task.options["field_path"] == "Project Field Data Dictionary.csv"

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
