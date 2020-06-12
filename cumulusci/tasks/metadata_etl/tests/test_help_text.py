import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.metadata_etl.help_text import AddHelpText
from cumulusci.utils.xml import metadata_tree

# Custom Object with 2 custom fields with all elements present
OBJECT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Buster__c</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by FERPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <inlineHelpText>Indicates that the Contact is allowed to receive information protected by FERPA and other privacy laws, regulations, and policies.</inlineHelpText>
        <label>FERPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
    <fields>
        <fullName>Bluth__c</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by HIPPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <inlineHelpText>Indicates that the Contact is allowed to receive information protected by HIPPA and other privacy laws, regulations, and policies.</inlineHelpText>
        <label>HIPPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
</CustomObject>
"""

# Additional Custom Object with 2 custom fields with all elements present
OBJECT_XML_2 = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Tobias__c</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by FERPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <inlineHelpText>Indicates that the Contact is allowed to receive information protected by FERPA and other privacy laws, regulations, and policies.</inlineHelpText>
        <label>FERPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
    <fields>
        <fullName>Bluth__c</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by HIPPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <inlineHelpText>Indicates arrested development.</inlineHelpText>
        <label>HIPPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
</CustomObject>
"""

# Custom Object with 2 custom fields witth Buster__c missing inlineHelpText
OBJECT_XML_3 = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Buster__c</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by FERPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <label>FERPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
    <fields>
        <fullName>Bluth__c</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by HIPPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <inlineHelpText>Indicates arrested development.</inlineHelpText>
        <label>HIPPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
</CustomObject>
"""

# Custom Object with 2 custom fields both missing inlineHelpText
OBJECT_XML_4 = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Buster__c</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by FERPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <label>FERPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
    <fields>
        <fullName>Bluth__c</fullName>
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
        <fullName>Buster</fullName>
        <defaultValue>false</defaultValue>
        <description>Indicates that the Contact is allowed to receive information protected by FERPA and other privacy laws, regulations, and policies.</description>
        <externalId>false</externalId>
        <label>FERPA Approved</label>
        <trackHistory>false</trackHistory>
        <trackTrending>false</trackTrending>
        <type>Checkbox</type>
    </fields>
    <fields>
        <fullName>Bluth</fullName>
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


class TestAddPicklistValues:
    def test_add_single_object_help_text(self):
        task = create_task(
            AddHelpText,
            {
                "api_version": "47.0",
                "entries": [
                    {"object_field": "MyObject.Buster__c", "help_text": "buster"}
                ],
            },
        )

        # Validate that the first sObject has one picklist changed
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        test_elem = result.find("fields", fullName="Buster__c")

        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "buster"
        # Validate that the sObject alters only the custom field listed
        test_elem = result.find("fields", fullName="Bluth__c")
        assert test_elem is not None
        assert (
            test_elem.inlineHelpText.text
            == "Indicates that the Contact is allowed to receive information protected by HIPPA and other privacy laws, regulations, and policies."
        )

    def test_add_multi_object_help_text(self):
        task = create_task(
            AddHelpText,
            {
                "api_version": "47.0",
                "entries": [
                    {"object_field": "MyObject.Buster__c", "help_text": "buster"},
                    {
                        "object_field": "MyObject2.Tobias__c",
                        "help_text": "george_michael",
                    },
                ],
            },
        )

        # Validate that the first sObject has one picklist changed
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        test_elem = result.find("fields", fullName="Buster__c")

        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "buster"
        # Validate that the first sObject alters only the custom field listed
        test_elem = result.find("fields", fullName="Bluth__c")
        assert test_elem is not None
        assert (
            test_elem.inlineHelpText.text
            == "Indicates that the Contact is allowed to receive information protected by HIPPA and other privacy laws, regulations, and policies."
        )
        tree = metadata_tree.fromstring(OBJECT_XML_2)
        result = task._transform_entity(tree, "MyObject2")
        test_elem = result.find("fields", fullName="Tobias__c")

        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "george_michael"

        test_elem = result.find("fields", fullName="Bluth__c")
        # Validate that the second sObject alters only the custom field listed: Tobias__c
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "Indicates arrested development."

    def test_add_single_object_multi_help_text(self):
        task = create_task(
            AddHelpText,
            {
                "api_version": "47.0",
                "entries": [
                    {"object_field": "MyObject.Buster__c", "help_text": "buster"},
                    {"object_field": "MyObject.Bluth__c", "help_text": "bluth"},
                ],
            },
        )

        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        # Validate that the first sObject has one picklist changed
        test_elem = result.find("fields", fullName="Buster__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "buster"
        # Validate that the first sObject alters only the custom field listed
        test_elem = result.find("fields", fullName="Bluth__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "bluth"

    def test_add_single_object_no_help_text(self):
        task = create_task(
            AddHelpText,
            {
                "api_version": "47.0",
                "entries": [
                    {"object_field": "MyObject3.Buster__c", "help_text": "buster"},
                    {"object_field": "MyObject3.Bluth__c", "help_text": "bluth"},
                ],
            },
        )

        tree = metadata_tree.fromstring(OBJECT_XML_3)
        result = task._transform_entity(tree, "MyObject3")
        # Validate that the first sObject has one picklist changed
        test_elem = result.find("fields", fullName="Buster__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "buster"
        # Validate that the first sObject alters only the custom field listed
        test_elem = result.find("fields", fullName="Bluth__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "bluth"

    def test_add_single_object_multi_field_no_help_text(self):
        task = create_task(
            AddHelpText,
            {
                "api_version": "47.0",
                "entries": [
                    {"object_field": "MyObject4.Buster__c", "help_text": "buster"},
                    {"object_field": "MyObject4.Bluth__c", "help_text": "bluth"},
                ],
            },
        )

        tree = metadata_tree.fromstring(OBJECT_XML_4)
        result = task._transform_entity(tree, "MyObject4")
        # Validate that the first sObject has one picklist changed
        test_elem = result.find("fields", fullName="Buster__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "buster"
        # Validate that the first sObject alters only the custom field listed
        test_elem = result.find("fields", fullName="Bluth__c")
        assert test_elem is not None
        assert test_elem.inlineHelpText.text == "bluth"

    def test_raises_for_no_entries(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(AddHelpText, {"api_version": "47.0"})

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_for_empty_entries(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(AddHelpText, {"api_version": "47.0", "entries": []})

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_for_non_list_entries(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                AddHelpText,
                {
                    "api_version": "47.0",
                    "entries": {
                        "object_field": "MyObject.Buster__c",
                        "help_text": "buster",
                    },
                },
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_no_entries_help_text(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                AddHelpText,
                {
                    "api_version": "47.0",
                    "entries": [{"object_field": "MyObject.Buster__c"}],
                },
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_no_entries_object_field(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                AddHelpText, {"api_version": "47.0", "entries": [{"help_text": "help"}]}
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_invalid_api_value(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                AddHelpText,
                {
                    "api_version": "buster_bluth",
                    "entries": [
                        {"object_field": "MyObject.Buster__c", "help_text": "help"}
                    ],
                },
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_for_standard_field_entries(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                AddHelpText,
                {
                    "api_version": "47.0",
                    "entries": [
                        {"object_field": "MyObject.Buster", "help_text": "buster"}
                    ],
                },
            )

            tree = metadata_tree.fromstring(STANDARD_OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_invalid_object(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                AddHelpText,
                {
                    "api_version": "48.0",
                    "entries": [
                        {"object_field": "Buster.b.Bust__c", "help_text": "help"}
                    ],
                },
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_api_version(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                AddHelpText,
                {
                    "api_version": "33.0",
                    "entries": [
                        {"object_field": "MyObject.Buster__c", "help_text": "help"}
                    ],
                },
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")

    def test_raises_missing_object(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                AddHelpText,
                {
                    "api_version": "48.0",
                    "entries": [
                        {"object_field": "MyObject.sherlock__c", "help_text": "help"}
                    ],
                },
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")
