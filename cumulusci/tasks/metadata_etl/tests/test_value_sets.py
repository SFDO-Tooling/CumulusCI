from lxml import etree
import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.metadata_etl import AddValueSetEntries
from cumulusci.tasks.metadata_etl import MD

VALUESET_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
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


class TestAddValueSetEntries:
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

        tree = etree.fromstring(VALUESET_XML).getroottree()

        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test']")) == 0
        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test_2']")) == 0

        result = task._transform_entity(tree, "ValueSet")

        entry = result.findall(f".//{MD}standardValue[{MD}fullName='Test']")
        assert len(entry) == 1
        label = entry[0].findall(f".//{MD}label")
        assert len(label) == 1
        assert label[0].text == "Label"
        default = entry[0].findall(f".//{MD}default")
        assert len(default) == 1
        assert default[0].text == "false"

        entry = result.findall(f".//{MD}standardValue[{MD}fullName='Test_2']")
        assert len(entry) == 1
        label = entry[0].findall(f".//{MD}label")
        assert len(label) == 1
        assert label[0].text == "Label 2"
        default = entry[0].findall(f".//{MD}default")
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

        tree = etree.fromstring(VALUESET_XML).getroottree()

        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test']")) == 0
        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test_2']")) == 0

        result = task._transform_entity(tree, "OpportunityStage")

        entry = result.findall(f".//{MD}standardValue[{MD}fullName='Test']")
        assert len(entry) == 1
        label = entry[0].findall(f".//{MD}label")
        assert len(label) == 1
        assert label[0].text == "Label"
        default = entry[0].findall(f".//{MD}default")
        assert len(default) == 1
        assert default[0].text == "false"
        closed = entry[0].findall(f".//{MD}closed")
        assert len(closed) == 1
        assert closed[0].text == "true"
        won = entry[0].findall(f".//{MD}won")
        assert len(won) == 1
        assert won[0].text == "true"
        forecastCategory = entry[0].findall(f".//{MD}forecastCategory")
        assert len(forecastCategory) == 1
        assert forecastCategory[0].text == "Omitted"
        probability = entry[0].findall(f".//{MD}probability")
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

        tree = etree.fromstring(VALUESET_XML).getroottree()

        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test']")) == 0
        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test_2']")) == 0

        result = task._transform_entity(tree, "CaseStatus")

        entry = result.findall(f".//{MD}standardValue[{MD}fullName='Test']")
        assert len(entry) == 1
        label = entry[0].findall(f".//{MD}label")
        assert len(label) == 1
        assert label[0].text == "Label"
        default = entry[0].findall(f".//{MD}default")
        assert len(default) == 1
        assert default[0].text == "false"
        closed = entry[0].findall(f".//{MD}closed")
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

        tree = etree.fromstring(VALUESET_XML).getroottree()

        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Value']")) == 1

        result = task._transform_entity(tree, "ValueSet")

        assert len(result.findall(f".//{MD}standardValue[{MD}fullName='Value']")) == 1

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
        tree = etree.fromstring(VALUESET_XML).getroottree()

        with pytest.raises(TaskOptionsError):
            task._transform_entity(tree, "ValueSet")

        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "entries": [{"label": "Value"}],
            },
        )

        with pytest.raises(TaskOptionsError):
            task._transform_entity(tree, "ValueSet")

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
        tree = etree.fromstring(VALUESET_XML).getroottree()

        with pytest.raises(TaskOptionsError) as err:
            task._transform_entity(tree, "OpportunityStage")
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
        tree = etree.fromstring(VALUESET_XML).getroottree()

        with pytest.raises(TaskOptionsError) as err:
            task._transform_entity(tree, "CaseStatus")
            assert "CaseStatus" in err
