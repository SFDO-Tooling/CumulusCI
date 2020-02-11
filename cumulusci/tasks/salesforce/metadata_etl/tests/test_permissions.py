import io
import unittest
import xml.etree.ElementTree as ET

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.salesforce.metadata_etl import AddPermissions

PERMSET_XML = """<?xml version="1.0" encoding="UTF-8"?>
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


class test_AddPermissions(unittest.TestCase):
    def test_adds_new_field_permission(self):
        task = create_task(
            AddPermissions,
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

        root = ET.ElementTree(file=io.StringIO(PERMSET_XML))
        namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

        assert (
            len(
                root.findall(
                    f".//sf:fieldPermissions[sf:field='Test__c.Description__c']",
                    namespaces,
                )
            )
            == 0
        )

        result = task._transform_entity(root, "PermSet")

        fieldPermissions = result.findall(
            ".//sf:fieldPermissions[sf:field='Test__c.Description__c']", namespaces
        )
        assert len(fieldPermissions) == 1
        readable = fieldPermissions[0].findall(f".//sf:readable", namespaces)
        assert len(readable) == 1
        assert readable[0].text == "true"
        editable = fieldPermissions[0].findall(f".//sf:editable", namespaces)
        assert len(editable) == 1
        assert editable[0].text == "true"

    def test_updates_existing_field_permission(self):
        task = create_task(
            AddPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "field_permissions": [
                    {"field": "Test__c.Lookup__c", "readable": True, "editable": True}
                ],
            },
        )

        root = ET.ElementTree(file=io.StringIO(PERMSET_XML))
        namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

        assert (
            len(
                root.findall(
                    f".//sf:fieldPermissions[sf:field='Test__c.Lookup__c']", namespaces
                )
            )
            == 1
        )

        result = task._transform_entity(root, "PermSet")

        fieldPermissions = result.findall(
            ".//sf:fieldPermissions[sf:field='Test__c.Lookup__c']", namespaces
        )
        assert len(fieldPermissions) == 1
        readable = fieldPermissions[0].findall(f".//sf:readable", namespaces)
        assert len(readable) == 1
        assert readable[0].text == "true"
        editable = fieldPermissions[0].findall(f".//sf:editable", namespaces)
        assert len(editable) == 1
        assert editable[0].text == "true"

    def test_adds_new_class_permission(self):
        task = create_task(
            AddPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "class_accesses": [{"apexClass": "LWCController", "enabled": True}],
            },
        )

        root = ET.ElementTree(file=io.StringIO(PERMSET_XML))
        namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

        assert (
            len(
                root.findall(
                    ".//sf:classAccesses[sf:apexClass='LWCController']", namespaces
                )
            )
            == 0
        )

        result = task._transform_entity(root, "PermSet")

        classAccesses = result.findall(
            ".//sf:classAccesses[sf:apexClass='LWCController']", namespaces
        )
        assert len(classAccesses) == 1
        enabled = classAccesses[0].findall(f".//sf:enabled", namespaces)
        assert len(enabled) == 1
        assert enabled[0].text == "true"

    def test_upserts_existing_class_permission(self):
        task = create_task(
            AddPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "class_accesses": [{"apexClass": "ApexController", "enabled": True}],
            },
        )

        root = ET.ElementTree(file=io.StringIO(PERMSET_XML))
        namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

        assert (
            len(
                root.findall(
                    ".//sf:classAccesses[sf:apexClass='ApexController']", namespaces
                )
            )
            == 1
        )

        result = task._transform_entity(root, "PermSet")

        classAccesses = result.findall(
            ".//sf:classAccesses[sf:apexClass='ApexController']", namespaces
        )
        assert len(classAccesses) == 1
        enabled = classAccesses[0].findall(f".//sf:enabled", namespaces)
        assert len(enabled) == 1
        assert enabled[0].text == "true"

    def test_missing_apexclass_throws_exception(self):
        task = create_task(
            AddPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "class_accesses": [{"enabled": True}],
            },
        )

        root = ET.ElementTree(file=io.StringIO(PERMSET_XML))

        with self.assertRaises(TaskOptionsError):
            task._transform_entity(root, "PermSet")

    def test_missing_field_throws_exception(self):
        task = create_task(
            AddPermissions,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "field_permissions": [{"readable": True}],
            },
        )

        root = ET.ElementTree(file=io.StringIO(PERMSET_XML))

        with self.assertRaises(TaskOptionsError):
            task._transform_entity(root, "PermSet")
