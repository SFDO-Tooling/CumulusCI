import logging

import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl.field_sets import AddFieldsToFieldSet
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.utils.xml import metadata_tree

OBJECT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fieldSets>
        <fullName>IncidentDetail</fullName>
        <availableFields>
            <field>IncidentDateTime__c</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </availableFields>
        <availableFields>
            <field>LocationNotes__c</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </availableFields>
        <availableFields>
            <field>WatchList__c</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </availableFields>
        <description>This field set is used by the Incidents component</description>
        <displayedFields>
            <field>ContactId</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </displayedFields>
        <displayedFields>
            <field>Subject</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </displayedFields>
        <displayedFields>
            <field>Description</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </displayedFields>
        <displayedFields>
            <field>IncidentType__c</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </displayedFields>
        <displayedFields>
            <field>CreatedDate</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </displayedFields>
        <displayedFields>
            <field>ClosedDate</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </displayedFields>
        <displayedFields>
            <field>Branch__c</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </displayedFields>
        <displayedFields>
            <field>Severity__c</field>
            <isFieldManaged>false</isFieldManaged>
            <isRequired>false</isRequired>
        </displayedFields>
        <label>Incident Detail</label>
    </fieldSets>
</CustomObject>
"""


class TestAddFieldsToFieldSet:
    def test_adds_fields(self):
        task = create_task(
            AddFieldsToFieldSet,
            {
                "field_set": "Case.IncidentDetail",
                "fields": ["IncidentDateTime__c", "LocationNotes__c"],
            },
        )

        # Validate that the fields have been added as displayedFields
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "Case")
        fields = result.find("fieldSets", fullName="IncidentDetail").findall(
            "displayedFields"
        )

        test_elems = [f for f in fields if f.field.text == "LocationNotes__c"]
        assert len(test_elems) == 1
        assert test_elems[0].isFieldManaged.text == "false"
        assert test_elems[0].isRequired.text == "false"

        test_elems = [f for f in fields if f.field.text == "LocationNotes__c"]
        assert len(test_elems) == 1
        assert test_elems[0].isFieldManaged.text == "false"
        assert test_elems[0].isRequired.text == "false"

        # Validate that the fields were removed from availableFields
        fields = result.find("fieldSets", fullName="IncidentDetail").findall(
            "availableFields"
        )
        assert "IncidentDateTime__c" not in (f.field.text for f in fields)
        assert "LocationNotes__c" not in (f.field.text for f in fields)

        # Validate that the other field remains in availableFields
        assert "WatchList__c" in (f.field.text for f in fields)

    def test_does_not_add_duplicate_values(self, caplog):
        task = create_task(
            AddFieldsToFieldSet,
            {
                "field_set": "Case.IncidentDetail",
                "fields": ["ContactId"],
            },
        )

        caplog.set_level(logging.INFO)

        # Validate that the duplicate entry is not added
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "Case")
        fields = result.find("fieldSets", fullName="IncidentDetail").findall(
            "displayedFields"
        )

        test_elems = [f for f in fields if f.field.text == "ContactId"]
        assert len(test_elems) == 1

        # Validate that info was logged
        assert "ContactId" in caplog.text

    def test_init_options__no_fields(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                AddFieldsToFieldSet,
                {
                    "field_set": "Case.IncidentDetail",
                },
            )

    def test_init_options__bad_picklist_name(self):
        task = create_task(
            AddFieldsToFieldSet,
            {
                "field_set": "Case.Garbage",
                "fields": ["IncidentDateTime__c", "LocationNotes__c"],
            },
        )
        tree = metadata_tree.fromstring(OBJECT_XML)
        with pytest.raises(TaskOptionsError):
            task._transform_entity(tree, "Case")
