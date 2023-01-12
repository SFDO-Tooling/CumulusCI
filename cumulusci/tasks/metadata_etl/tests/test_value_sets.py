import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import AddValueSetEntries
from cumulusci.tasks.metadata_etl.value_sets import (
    CASE_STATUS_ERR,
    FULL_NAME_AND_LABEL_ERR,
    LEAD_STATUS_ERR,
    OPP_STAGE_ERR,
)
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.utils.xml import lxml_parse_string, metadata_tree

MD = "{%s}" % "http://soap.sforce.com/2006/04/metadata"
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

        tree = lxml_parse_string(VALUESET_XML)

        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test']")) == 0
        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test_2']")) == 0

        result = task._transform_entity(
            metadata_tree.fromstring(VALUESET_XML), "ValueSet"
        )

        entry = result._element.findall(f".//{MD}standardValue[{MD}fullName='Test']")
        assert len(entry) == 1
        label = entry[0].findall(f".//{MD}label")
        assert len(label) == 1
        assert label[0].text == "Label"
        default = entry[0].findall(f".//{MD}default")
        assert len(default) == 1
        assert default[0].text == "false"

        entry = result._element.findall(f".//{MD}standardValue[{MD}fullName='Test_2']")
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

        tree = metadata_tree.fromstring(VALUESET_XML)

        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test']")) == 0
        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test_2']")) == 0

        result = task._transform_entity(tree, "OpportunityStage")

        entry = result._element.findall(f".//{MD}standardValue[{MD}fullName='Test']")
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

        tree = lxml_parse_string(VALUESET_XML)

        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test']")) == 0
        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test_2']")) == 0

        result = task._transform_entity(
            metadata_tree.fromstring(VALUESET_XML), "CaseStatus"
        )

        entry = result._element.findall(f".//{MD}standardValue[{MD}fullName='Test']")
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

    def test_adds_entry__leadStatus(self):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "LeadStatus",
                "entries": [{"fullName": "Test", "label": "Label", "converted": True}],
            },
        )

        tree = lxml_parse_string(VALUESET_XML)

        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test']")) == 0
        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Test_2']")) == 0

        result = task._transform_entity(
            metadata_tree.fromstring(VALUESET_XML), "LeadStatus"
        )

        entry = result._element.findall(f".//{MD}standardValue[{MD}fullName='Test']")
        assert len(entry) == 1
        label = entry[0].findall(f".//{MD}label")
        assert len(label) == 1
        assert label[0].text == "Label"
        default = entry[0].findall(f".//{MD}default")
        assert len(default) == 1
        assert default[0].text == "false"
        converted = entry[0].findall(f".//{MD}converted")
        assert len(converted) == 1
        assert converted[0].text == "true"

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

        tree = lxml_parse_string(VALUESET_XML)

        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Value']")) == 1

        metadata = metadata_tree.fromstring(VALUESET_XML)
        task._transform_entity(metadata, "ValueSet")

        assert len(tree.findall(f".//{MD}standardValue[{MD}fullName='Value']")) == 1

    entries = [
        {},
        {"fullName": "Value"},
        {"label": "Value"},
    ]

    @pytest.mark.parametrize("entry", entries)
    def test_raises_exception_missing_values(self, entry):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "entries": [entry],
            },
        )
        tree = metadata_tree.fromstring(VALUESET_XML)

        with pytest.raises(TaskOptionsError, match=FULL_NAME_AND_LABEL_ERR):
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
        tree = metadata_tree.fromstring(VALUESET_XML)

        with pytest.raises(TaskOptionsError, match=OPP_STAGE_ERR):
            task._transform_entity(tree, "OpportunityStage")

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
        tree = metadata_tree.fromstring(VALUESET_XML)

        with pytest.raises(TaskOptionsError, match=CASE_STATUS_ERR):
            task._transform_entity(tree, "CaseStatus")

    def test_raises_exception_missing_values__leadstatus(self):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "LeadStatus",
                "entries": [{"fullName": "Value", "label": "Value"}],
            },
        )
        tree = metadata_tree.fromstring(VALUESET_XML)

        with pytest.raises(TaskOptionsError, match=LEAD_STATUS_ERR):
            task._transform_entity(tree, "LeadStatus")

    def test_adds_correct_number_of_values(self):
        task = create_task(
            AddValueSetEntries,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "entries": [
                    {"fullName": "Test", "label": "Label"},
                    {"fullName": "Test_2", "label": "Label 2"},
                    {"fullName": "Other", "label": "Duplicate"},
                ],
            },
        )

        mdtree = metadata_tree.fromstring(VALUESET_XML)
        xml_tree = mdtree._element

        assert len(xml_tree.findall(f".//{MD}standardValue")) == 2

        task._transform_entity(mdtree, "ValueSet")

        assert len(xml_tree.findall(f".//{MD}standardValue")) == 4
