import io
import unittest
import xml.etree.ElementTree as ET

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.salesforce.metadata_etl import AddValueSetEntries

VALUESET_XML = """<?xml version="1.0" encoding="UTF-8"?>
<StandardValueSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <sorted>false</sorted>
    <standardValue>
        <fullName>Value</fullName>
        <default>true</default>
        <label>Value</label>
    </standardValue>
    <standardValue>
        <fullName>Other</fullName>
        <default>false</default>
        <label>Other</label>
    </standardValue>
</StandardValueSet>
"""


class test_AddValueSetEntries(unittest.TestCase):
    def test_adds_entry(self):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "entries": [
                    {"fullName": "Test", "label": "Label"},
                    {"fullName": "Test_2", "label": "Label 2"},
                ],
            },
        )

        root = ET.ElementTree(file=io.StringIO(VALUESET_XML))
        namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

        assert (
            len(root.findall(".//sf:standardValue[sf:fullName='Test']", namespaces))
            == 0
        )
        assert (
            len(root.findall(".//sf:standardValue[sf:fullName='Test_2']", namespaces))
            == 0
        )

        result = task._transform_entity(root, "ValueSet")

        entry = result.findall(".//sf:standardValue[sf:fullName='Test']", namespaces)
        assert len(entry) == 1
        label = entry[0].findall(f".//sf:label", namespaces)
        assert len(label) == 1
        assert label[0].text == "Label"
        default = entry[0].findall(f".//sf:default", namespaces)
        assert len(default) == 1
        assert default[0].text == "false"

        entry = result.findall(".//sf:standardValue[sf:fullName='Test_2']", namespaces)
        assert len(entry) == 1
        label = entry[0].findall(f".//sf:label", namespaces)
        assert len(label) == 1
        assert label[0].text == "Label 2"
        default = entry[0].findall(f".//sf:default", namespaces)
        assert len(default) == 1
        assert default[0].text == "false"

    def test_adds_entry__opportunitystage(self):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "OpportunityStage",
                "entries": [
                    {
                        "fullName": "Test",
                        "label": "Label",
                        "closed": True,
                        "won": True,
                        "forecastCategory": "Omitted",
                        "probability": 100,
                    }
                ],
            },
        )

        root = ET.ElementTree(file=io.StringIO(VALUESET_XML))
        namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

        assert (
            len(root.findall(".//sf:standardValue[sf:fullName='Test']", namespaces))
            == 0
        )
        assert (
            len(root.findall(".//sf:standardValue[sf:fullName='Test_2']", namespaces))
            == 0
        )

        result = task._transform_entity(root, "OpportunityStage")

        entry = result.findall(".//sf:standardValue[sf:fullName='Test']", namespaces)
        assert len(entry) == 1
        label = entry[0].findall(f".//sf:label", namespaces)
        assert len(label) == 1
        assert label[0].text == "Label"
        default = entry[0].findall(f".//sf:default", namespaces)
        assert len(default) == 1
        assert default[0].text == "false"
        closed = entry[0].findall(f".//sf:closed", namespaces)
        assert len(closed) == 1
        assert closed[0].text == "true"
        won = entry[0].findall(f".//sf:won", namespaces)
        assert len(won) == 1
        assert won[0].text == "true"
        forecastCategory = entry[0].findall(f".//sf:forecastCategory", namespaces)
        assert len(forecastCategory) == 1
        assert forecastCategory[0].text == "Omitted"
        probability = entry[0].findall(f".//sf:probability", namespaces)
        assert len(probability) == 1
        assert probability[0].text == "100"

    def test_adds_entry__casestatus(self):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "CaseStatus",
                "entries": [{"fullName": "Test", "label": "Label", "closed": True}],
            },
        )

        root = ET.ElementTree(file=io.StringIO(VALUESET_XML))
        namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

        assert (
            len(root.findall(".//sf:standardValue[sf:fullName='Test']", namespaces))
            == 0
        )
        assert (
            len(root.findall(".//sf:standardValue[sf:fullName='Test_2']", namespaces))
            == 0
        )

        result = task._transform_entity(root, "CaseStatus")

        entry = result.findall(".//sf:standardValue[sf:fullName='Test']", namespaces)
        assert len(entry) == 1
        label = entry[0].findall(f".//sf:label", namespaces)
        assert len(label) == 1
        assert label[0].text == "Label"
        default = entry[0].findall(f".//sf:default", namespaces)
        assert len(default) == 1
        assert default[0].text == "false"
        closed = entry[0].findall(f".//sf:closed", namespaces)
        assert len(closed) == 1
        assert closed[0].text == "true"

    def test_does_not_add_existing_entry(self):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "entries": [{"fullName": "Value", "label": "Label"}],
            },
        )

        root = ET.ElementTree(file=io.StringIO(VALUESET_XML))
        namespaces = {"sf": "http://soap.sforce.com/2006/04/metadata"}

        assert (
            len(root.findall(".//sf:standardValue[sf:fullName='Value']", namespaces))
            == 1
        )

        result = task._transform_entity(root, "ValueSet")

        assert (
            len(result.findall(".//sf:standardValue[sf:fullName='Value']", namespaces))
            == 1
        )

    def test_raises_exception_missing_values(self):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "entries": [{"fullName": "Value"}],
            },
        )
        root = ET.ElementTree(file=io.StringIO(VALUESET_XML))

        with self.assertRaises(TaskOptionsError):
            task._transform_entity(root, "ValueSet")

        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "entries": [{"label": "Value"}],
            },
        )

        with self.assertRaises(TaskOptionsError):
            task._transform_entity(root, "ValueSet")

    def test_raises_exception_missing_values__opportunitystage(self):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "OpportunityStage",
                "entries": [{"fullName": "Value", "label": "Value"}],
            },
        )
        root = ET.ElementTree(file=io.StringIO(VALUESET_XML))

        with self.assertRaises(TaskOptionsError) as err:
            task._transform_entity(root, "OpportunityStage")
            assert "OpportunityStage" in err

    def test_raises_exception_missing_values__casestatus(self):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "CaseStatus",
                "entries": [{"fullName": "Value", "label": "Value"}],
            },
        )
        root = ET.ElementTree(file=io.StringIO(VALUESET_XML))

        with self.assertRaises(TaskOptionsError) as err:
            task._transform_entity(root, "CaseStatus")
            assert "CaseStatus" in err
