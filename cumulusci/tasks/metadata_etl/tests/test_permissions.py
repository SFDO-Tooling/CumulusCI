from lxml import etree
import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.metadata_etl import AddPermissionSetPermissions
from cumulusci.tasks.metadata_etl import MD

PERMSET_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <applicationVisibilities>
        <application>CustomApp</application>
        <visible>false</visible>
    </applicationVisibilities>
    <classAccesses>
        <apexClass>ApexController</apexClass>
        <enabled>false</enabled>
    </classAccesses>
    <fieldPermissions>
        <editable>false</editable>
        <field>Test__c.Lookup__c</field>
        <readable>false</readable>
    </fieldPermissions>
    <hasActivationRequired>false</hasActivationRequired>
    <label>Test</label>
    <objectPermissions>
        <allowCreate>false</allowCreate>
        <allowDelete>false</allowDelete>
        <allowEdit>false</allowEdit>
        <allowRead>false</allowRead>
        <modifyAllRecords>false</modifyAllRecords>
        <object>Test__c</object>
        <viewAllRecords>false</viewAllRecords>
    </objectPermissions>
    <recordTypeVisibilities>
        <recordType>Case.Test</recordType>
        <visible>true</visible>
    </recordTypeVisibilities>
    <tabSettings>
        <tab>standard-report</tab>
        <visibility>Visible</visibility>
    </tabSettings>
    <userPermissions>
        <enabled>true</enabled>
        <name>ActivitiesAccess</name>
    </userPermissions>
</PermissionSet>
"""


class TestAddPermissionSetPermissions:
    def test_adds_new_field_permission(self):
        task = create_task(
            AddPermissionSetPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "field_permissions": [
                    {
                        "field": "Test__c.Description__c",
                        "readable": True,
                        "editable": True,
                    }
                ],
            },
        )

        tree = etree.fromstring(PERMSET_XML).getroottree()

        assert (
            len(
                tree.findall(
                    f".//{MD}fieldPermissions[{MD}field='Test__c.Description__c']"
                )
            )
            == 0
        )

        result = task._transform_entity(tree, "PermSet")

        fieldPermissions = result.findall(
            f".//{MD}fieldPermissions[{MD}field='Test__c.Description__c']"
        )
        assert len(fieldPermissions) == 1
        readable = fieldPermissions[0].findall(f".//{MD}readable")
        assert len(readable) == 1
        assert readable[0].text == "true"
        editable = fieldPermissions[0].findall(f".//{MD}editable")
        assert len(editable) == 1
        assert editable[0].text == "true"

    def test_updates_existing_field_permission(self):
        task = create_task(
            AddPermissionSetPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "field_permissions": [
                    {"field": "Test__c.Lookup__c", "readable": True, "editable": True}
                ],
            },
        )

        tree = etree.fromstring(PERMSET_XML).getroottree()

        assert (
            len(tree.findall(f".//{MD}fieldPermissions[{MD}field='Test__c.Lookup__c']"))
            == 1
        )

        result = task._transform_entity(tree, "PermSet")

        fieldPermissions = result.findall(
            f".//{MD}fieldPermissions[{MD}field='Test__c.Lookup__c']"
        )
        assert len(fieldPermissions) == 1
        readable = fieldPermissions[0].findall(f".//{MD}readable")
        assert len(readable) == 1
        assert readable[0].text == "true"
        editable = fieldPermissions[0].findall(f".//{MD}editable")
        assert len(editable) == 1
        assert editable[0].text == "true"

    def test_adds_new_class_permission(self):
        task = create_task(
            AddPermissionSetPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "class_accesses": [{"apexClass": "LWCController", "enabled": True}],
            },
        )

        tree = etree.fromstring(PERMSET_XML).getroottree()

        assert (
            len(tree.findall(f".//{MD}classAccesses[{MD}apexClass='LWCController']"))
            == 0
        )

        result = task._transform_entity(tree, "PermSet")

        classAccesses = result.findall(
            f".//{MD}classAccesses[{MD}apexClass='LWCController']"
        )
        assert len(classAccesses) == 1
        enabled = classAccesses[0].findall(f".//{MD}enabled")
        assert len(enabled) == 1
        assert enabled[0].text == "true"

    def test_upserts_existing_class_permission(self):
        task = create_task(
            AddPermissionSetPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "class_accesses": [{"apexClass": "ApexController", "enabled": True}],
            },
        )

        tree = etree.fromstring(PERMSET_XML).getroottree()

        assert (
            len(tree.findall(f".//{MD}classAccesses[{MD}apexClass='ApexController']"))
            == 1
        )

        result = task._transform_entity(tree, "PermSet")

        classAccesses = result.findall(
            f".//{MD}classAccesses[{MD}apexClass='ApexController']"
        )
        assert len(classAccesses) == 1
        enabled = classAccesses[0].findall(f".//{MD}enabled")
        assert len(enabled) == 1
        assert enabled[0].text == "true"

    def test_missing_apexclass_throws_exception(self):
        task = create_task(
            AddPermissionSetPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "class_accesses": [{"enabled": True}],
            },
        )

        tree = etree.fromstring(PERMSET_XML).getroottree()

        with pytest.raises(TaskOptionsError):
            task._transform_entity(tree, "PermSet")

    def test_missing_field_throws_exception(self):
        task = create_task(
            AddPermissionSetPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "field_permissions": [{"readable": True}],
            },
        )

        tree = etree.fromstring(PERMSET_XML).getroottree()

        with pytest.raises(TaskOptionsError):
            task._transform_entity(tree, "PermSet")
