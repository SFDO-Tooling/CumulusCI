import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.metadata_etl.help_text import SetFieldHelpText
from cumulusci.utils.xml import metadata_tree

# Custom Object with 2 custom fields with all elements present
OBJECT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Foo__c</fullName>
        <inlineHelpText>Foo</inlineHelpText>
    </fields>
    <fields>
        <fullName>Bar__c</fullName>
        <inlineHelpText>Bar</inlineHelpText>
    </fields>
</CustomObject>
"""

# Additional Custom Object with 2 custom fields with all elements present
OBJECT_XML_2 = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Foo__c</fullName>
        <inlineHelpText>Foo</inlineHelpText>
    </fields>
    <fields>
        <fullName>Bar__c</fullName>
        <inlineHelpText>Does something.</inlineHelpText>
    </fields>
</CustomObject>
"""

# Custom Object with 2 custom fields with one missing inlineHelpText
OBJECT_XML_3 = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Foo__c</fullName>
    </fields>
    <fields>
        <fullName>Bar__c</fullName>
        <inlineHelpText>Does something.</inlineHelpText>
    </fields>
</CustomObject>
"""

# Custom Object with 2 custom fields both missing inlineHelpText
OBJECT_XML_4 = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Foo__c</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by FERPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <label>FERPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
    <fields>
        <fullName>Bar__c</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by HIPPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <label>HIPPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
</CustomObject>
"""

STANDARD_OBJECT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Foo</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by FERPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <label>FERPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
    <fields>
        <fullName>Bar</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by HIPPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <inlineHelpText>Foo</inlineHelpText>
        <label>HIPPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
</CustomObject>
"""


class TestAddPicklistValues:
    def test_add_single_object_help_text(self):
        task = create_task(
            SetFieldHelpText,
            {
                "api_version": "47.0",
                "overwrite": True,
                "fields": [{"api_name": "MyObject.Foo__c", "help_text": "foo"}],
            },
        )

        # Validate that the first sObject has one picklist changed
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        test_elem = result.find("fields", fullName="Foo__c")

        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "foo"
        # Validate that the sObject alters only the custom field listed
        test_elem = result.find("fields", fullName="Bar__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "Bar"

    def test_add_single_object_help_text__same_value(self):
        task = create_task(
            SetFieldHelpText,
            {
                "api_version": "47.0",
                "overwrite": True,
                "fields": [{"api_name": "MyObject.Foo__c", "help_text": "foo"}],
            },
        )

        tree = metadata_tree.fromstring(OBJECT_XML)
        test_elem = tree.find("fields", fullName="Foo__c")
        test_elem.inlineHelpText.text = "foo"
        assert task._transform_entity(tree, "MyObject") is tree

        assert test_elem.inlineHelpText.text == "foo"

    def test_add_single_object_help_text__blank_value(self):
        task = create_task(
            SetFieldHelpText,
            {
                "api_version": "47.0",
                "overwrite": True,
                "fields": [{"api_name": "MyObject.Foo__c", "help_text": "foo"}],
            },
        )

        tree = metadata_tree.fromstring(OBJECT_XML)
        test_elem = tree.find("fields", fullName="Foo__c")
        test_elem.inlineHelpText.text = ""
        assert task._transform_entity(tree, "MyObject") is tree

        assert test_elem.inlineHelpText.text == "foo"

    def test_add_multi_object_help_text(self):
        task = create_task(
            SetFieldHelpText,
            {
                "api_version": "47.0",
                "overwrite": True,
                "fields": [
                    {"api_name": "MyObject.Foo__c", "help_text": "foo"},
                    {"api_name": "MyObject2.Bar__c", "help_text": "bar"},
                ],
            },
        )

        # Validate that the first sObject has one picklist changed
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        test_elem = result.find("fields", fullName="Foo__c")

        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "foo"
        # Validate that the first sObject alters only the custom field listed
        test_elem = result.find("fields", fullName="Bar__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "Bar"
        tree = metadata_tree.fromstring(OBJECT_XML_2)
        result = task._transform_entity(tree, "MyObject2")
        test_elem = result.find("fields", fullName="Bar__c")

        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "bar"

        test_elem = result.find("fields", fullName="Foo__c")
        # Validate that the second sObject alters only the custom field listed: Tobias__c
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "Foo"

    def test_add_single_object_multi_help_text(self):
        task = create_task(
            SetFieldHelpText,
            {
                "api_version": "47.0",
                "overwrite": True,
                "fields": [
                    {"api_name": "MyObject.Foo__c", "help_text": "foo"},
                    {"api_name": "MyObject.Bar__c", "help_text": "bar"},
                ],
            },
        )

        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        # Validate that the first sObject has one picklist changed
        test_elem = result.find("fields", fullName="Foo__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "foo"
        # Validate that the first sObject alters only the custom field listed
        test_elem = result.find("fields", fullName="Bar__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "bar"

    def test_add_single_object_no_help_text(self):
        task = create_task(
            SetFieldHelpText,
            {
                "api_version": "47.0",
                "overwrite": True,
                "fields": [
                    {"api_name": "MyObject3.Foo__c", "help_text": "foo"},
                    {"api_name": "MyObject3.Bar__c", "help_text": "bar"},
                ],
            },
        )

        tree = metadata_tree.fromstring(OBJECT_XML_3)
        result = task._transform_entity(tree, "MyObject3")
        # Validate that the first sObject has one picklist changed
        test_elem = result.find("fields", fullName="Foo__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "foo"
        # Validate that the first sObject alters only the custom field listed
        test_elem = result.find("fields", fullName="Bar__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "bar"

    def test_add_single_object_multi_field_no_help_text(self):
        task = create_task(
            SetFieldHelpText,
            {
                "api_version": "47.0",
                "overwrite": True,
                "fields": [
                    {"api_name": "MyObject4.Foo__c", "help_text": "foo"},
                    {"api_name": "MyObject4.Bar__c", "help_text": "bar"},
                ],
            },
        )

        tree = metadata_tree.fromstring(OBJECT_XML_4)
        result = task._transform_entity(tree, "MyObject4")
        # Validate that the first sObject has one picklist changed
        test_elem = result.find("fields", fullName="Foo__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "foo"
        # Validate that the first sObject alters only the custom field listed
        test_elem = result.find("fields", fullName="Bar__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "bar"

    def test_raises_for_empty_fields(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(SetFieldHelpText, {"api_version": "47.0", "fields": []})

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_for_non_list_fields(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                SetFieldHelpText,
                {
                    "api_version": "47.0",
                    "fields": {"api_name": "MyObject.Foo__c", "help_text": "foo"},
                },
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_no_fields_help_text(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                SetFieldHelpText,
                {"api_version": "47.0", "fields": [{"api": "MyObject.Foo__c"}]},
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_no_fields_api(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                SetFieldHelpText,
                {"api_version": "47.0", "fields": [{"help_text": "help"}]},
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_sets_helptext_for_standard_field_fields(self):
        task = create_task(
            SetFieldHelpText,
            {
                "api_version": "47.0",
                "overwrite": True,
                "fields": [
                    {"api_name": "MyObject.Foo", "help_text": "foo"},
                    {"api_name": "MyObject.Bar", "help_text": "bar"},
                ],
            },
        )

        tree = metadata_tree.fromstring(STANDARD_OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        test_elem = result.find("fields", fullName="Foo")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "foo"

        test_elem = result.find("fields", fullName="Bar")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "bar"

    def test_raises_for_no_help_text_field(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                SetFieldHelpText,
                {
                    "api_version": "47.0",
                    "fields": [{"api_name": "MyObject.Foo", "bar": "buster_name"}],
                },
            )

            tree = metadata_tree.fromstring(STANDARD_OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_invalid_object(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                SetFieldHelpText,
                {
                    "api_version": "48.0",
                    "fields": [{"api_name": "Test.c.Test__c", "help_text": "help"}],
                },
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_missing_object(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                SetFieldHelpText,
                {
                    "api_version": "48.0",
                    "fields": [
                        {"api_name": "MyObject.sherlock__c", "help_text": "help"}
                    ],
                },
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_overwrite_false(self):
        task = create_task(
            SetFieldHelpText,
            {
                "api_version": "47.0",
                "overwrite": False,
                "fields": [{"api_name": "MyObject.Foo__c", "help_text": "foo"}],
            },
        )

        # Validate that the first sObject has one picklist changed
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        test_elem = result.find("fields", fullName="Foo__c")

        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "Foo"
