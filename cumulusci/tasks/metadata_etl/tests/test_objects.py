import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import SetObjectSettings
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.utils.xml import metadata_tree

MD = "{%s}" % metadata_tree.METADATA_NAMESPACE

CUSTOMOBJECT_SETTINGS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingModel>Read</sharingModel>
    <externalSharingModel>Read</externalSharingModel>
    <label>Test</label>
    <pluralLabel>Tests</pluralLabel>
    <nameField>
        <label>Test Name</label>
        <trackHistory>false</trackHistory>
        <type>Text</type>
    </nameField>
    <deploymentStatus>Deployed</deploymentStatus>
    <enableActivities>true</enableActivities>
    <enableBulkApi>true</enableBulkApi>
    <enableFeeds>false</enableFeeds>
    <enableHistory>false</enableHistory>
</CustomObject>"""


class TestSetObjectSettings:
    def test_options__require_enable_or_disable(self):
        with pytest.raises(TaskOptionsError) as e:
            create_task(
                SetObjectSettings,
                {
                    "api_names": "Test__c",
                },
            )
        assert (
            e.value.args[0]
            == "You must provide values for either 'enable' or 'disable'"
        )

    def test_options__invalid_setting(self):
        with pytest.raises(TaskOptionsError) as e:
            create_task(
                SetObjectSettings,
                {
                    "api_names": "Test__c",
                    "enable": ["Foo"],
                },
            )
        assert e.value.args[0].startswith("Invalid settings: Foo.")

    def test_options__invalid_settings(self):
        with pytest.raises(TaskOptionsError) as e:
            create_task(
                SetObjectSettings,
                {
                    "api_names": "Test__c",
                    "enable": ["Foo", "Bar"],
                },
            )
        assert e.value.args[0].startswith("Invalid settings: Foo, Bar.")

    def test_enable__single(self):
        task = create_task(
            SetObjectSettings,
            {
                "api_names": "Test__c",
                "enable": ["Feeds"],
            },
        )
        tree = metadata_tree.fromstring(CUSTOMOBJECT_SETTINGS_XML)

        result = task._transform_entity(tree, "Test__c")

        entry = result._element.findall(f".//{MD}enableFeeds")
        assert len(entry) == 1
        assert entry[0].text == "true"

        entry = result._element.findall(f".//{MD}enableHistory")
        assert len(entry) == 1
        assert entry[0].text == "false"

    def test_enable__single_missing(self):
        task = create_task(
            SetObjectSettings,
            {
                "api_names": "Test__c",
                "enable": ["Sharing"],
            },
        )
        tree = metadata_tree.fromstring(CUSTOMOBJECT_SETTINGS_XML)

        result = task._transform_entity(tree, "Test__c")

        entry = result._element.findall(f".//{MD}enableSharing")
        assert len(entry) == 1
        assert entry[0].text == "true"

    def test_enable__no_change(self):
        task = create_task(
            SetObjectSettings,
            {
                "api_names": "Test__c",
                "enable": ["Activities"],
            },
        )
        tree = metadata_tree.fromstring(CUSTOMOBJECT_SETTINGS_XML)

        result = task._transform_entity(tree, "Test__c")

        entry = result._element.findall(f".//{MD}enableActivities")
        assert len(entry) == 1
        assert entry[0].text == "true"

    def test_enable__multiple(self):
        task = create_task(
            SetObjectSettings,
            {
                "api_names": "Test__c",
                "enable": ["Feeds", "History"],
            },
        )
        tree = metadata_tree.fromstring(CUSTOMOBJECT_SETTINGS_XML)

        result = task._transform_entity(tree, "Test__c")

        entry = result._element.findall(f".//{MD}enableFeeds")
        assert len(entry) == 1
        assert entry[0].text == "true"

        entry = result._element.findall(f".//{MD}enableHistory")
        assert len(entry) == 1
        assert entry[0].text == "true"

    def test_disable__single(self):
        task = create_task(
            SetObjectSettings,
            {
                "api_names": "Test__c",
                "disable": ["Activities"],
            },
        )
        tree = metadata_tree.fromstring(CUSTOMOBJECT_SETTINGS_XML)

        result = task._transform_entity(tree, "Test__c")

        entry = result._element.findall(f".//{MD}enableActivities")
        assert len(entry) == 1
        assert entry[0].text == "false"

        entry = result._element.findall(f".//{MD}enableBulkApi")
        assert len(entry) == 1
        assert entry[0].text == "true"

    def test_disable__single_missing(self):
        task = create_task(
            SetObjectSettings,
            {
                "api_names": "Test__c",
                "disable": ["Sharing"],
            },
        )
        tree = metadata_tree.fromstring(CUSTOMOBJECT_SETTINGS_XML)

        result = task._transform_entity(tree, "Test__c")

        entry = result._element.findall(f".//{MD}enableSharing")
        assert len(entry) == 1
        assert entry[0].text == "false"

    def test_disable__no_change(self):
        task = create_task(
            SetObjectSettings,
            {
                "api_names": "Test__c",
                "disable": ["Feeds"],
            },
        )
        tree = metadata_tree.fromstring(CUSTOMOBJECT_SETTINGS_XML)

        result = task._transform_entity(tree, "Test__c")

        entry = result._element.findall(f".//{MD}enableFeeds")
        assert len(entry) == 1
        assert entry[0].text == "false"

    def test_disable__multiple(self):
        task = create_task(
            SetObjectSettings,
            {
                "api_names": "Test__c",
                "disable": ["Activities", "BulkApi"],
            },
        )
        tree = metadata_tree.fromstring(CUSTOMOBJECT_SETTINGS_XML)

        result = task._transform_entity(tree, "Test__c")

        entry = result._element.findall(f".//{MD}enableActivities")
        assert len(entry) == 1
        assert entry[0].text == "false"

        entry = result._element.findall(f".//{MD}enableBulkApi")
        assert len(entry) == 1
        assert entry[0].text == "false"

    def test_enable_and_disable(self):
        task = create_task(
            SetObjectSettings,
            {
                "api_names": "Test__c",
                "enable": ["Feeds", "History"],
                "disable": ["Activities", "BulkApi"],
            },
        )
        tree = metadata_tree.fromstring(CUSTOMOBJECT_SETTINGS_XML)

        result = task._transform_entity(tree, "Test__c")

        entry = result._element.findall(f".//{MD}enableActivities")
        assert len(entry) == 1
        assert entry[0].text == "false"

        entry = result._element.findall(f".//{MD}enableBulkApi")
        assert len(entry) == 1
        assert entry[0].text == "false"

        entry = result._element.findall(f".//{MD}enableFeeds")
        assert len(entry) == 1
        assert entry[0].text == "true"

        entry = result._element.findall(f".//{MD}enableHistory")
        assert len(entry) == 1
        assert entry[0].text == "true"
