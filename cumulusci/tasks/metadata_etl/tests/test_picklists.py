import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.metadata_etl.picklists import AddPicklistEntries
from cumulusci.utils.xml import metadata_tree

OBJECT_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Time_Zone__c</fullName>
        <type>Picklist</type>
        <valueSet>
            <valueSetDefinition>
                <sorted>false</sorted>
                <value>
                    <fullName>Pacific/Kiritimati</fullName>
                    <default>false</default>
                </value>
                <value>
                    <fullName>Pacific/Chatham</fullName>
                    <default>true</default>
                </value>
            </valueSetDefinition>
        </valueSet>
    </fields>
    <fields>
        <fullName>Type__c</fullName>
        <type>Picklist</type>
        <valueSet>
            <valueSetDefinition>
                <sorted>true</sorted>
                <value>
                    <fullName>Fundraising</fullName>
                    <default>false</default>
                </value>
                <value>
                    <fullName>Outreach</fullName>
                    <default>true</default>
                </value>
            </valueSetDefinition>
        </valueSet>
    </fields>
    <fields>
        <fullName>TestGVS__c</fullName>
        <externalId>false</externalId>
        <label>TestGVS</label>
        <required>false</required>
        <trackFeedHistory>false</trackFeedHistory>
        <type>Picklist</type>
        <valueSet>
            <restricted>true</restricted>
            <valueSetName>Test</valueSetName>
        </valueSet>
    </fields>
    <recordTypes>
        <fullName>Default_RT</fullName>
        <active>true</active>
        <picklistValues>
            <picklist>Type__c</picklist>
            <values>
                <fullName>Fundraising</fullName>
                <default>false</default>
            </values>
            <values>
                <fullName>Outreach</fullName>
                <default>true</default>
            </values>
        </picklistValues>
        <picklistValues>
            <picklist>Time_Zone__c</picklist>
            <values>
                <fullName>Pacific%2FKiritimati</fullName>
                <default>false</default>
            </values>
            <values>
                <fullName>Pacific%2FChatham</fullName>
                <default>false</default>
            </values>
        </picklistValues>
    </recordTypes>
    <recordTypes>
        <fullName>Second_RT</fullName>
        <active>true</active>
        <picklistValues>
            <picklist>Type__c</picklist>
            <values>
                <fullName>Fundraising</fullName>
                <default>false</default>
            </values>
            <values>
                <fullName>Outreach</fullName>
                <default>true</default>
            </values>
        </picklistValues>
        <picklistValues>
            <picklist>Time_Zone__c</picklist>
            <values>
                <fullName>Pacific%2FKiritimati</fullName>
                <default>false</default>
            </values>
            <values>
                <fullName>Pacific%2FChatham</fullName>
                <default>false</default>
            </values>
        </picklistValues>
    </recordTypes>
</CustomObject>
"""


class TestAddPicklistValues:
    def test_adds_values(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                "entries": [
                    {"fullName": "Test"},
                    {"fullName": "Foo", "label": "Bar", "default": True},
                ],
            },
        )

        # Validate that the first sObject has one picklist changed
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        values = result.find(
            "fields", fullName="Time_Zone__c"
        ).valueSet.valueSetDefinition.value

        test_elem = next(v for v in values if v.fullName.text == "Test")
        assert test_elem is not None
        assert test_elem.label.text == "Test"
        assert test_elem.default.text == "false"

        test_elem = next(v for v in values if v.fullName.text == "Foo")
        assert test_elem is not None
        assert test_elem.label.text == "Bar"
        assert test_elem.default.text == "true"

        test_elem = next(v for v in values if v.fullName.text == "Pacific/Chatham")
        assert test_elem.default.text == "false"

        # Show that the other picklist is unaffected
        values = result.find(
            "fields", fullName="Type__c"
        ).valueSet.valueSetDefinition.value
        assert "Test" not in (v.fullName.text for v in values)

    def test_does_not_add_duplicate_values(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                "entries": [{"fullName": "Outreach"}],
            },
        )

        # Validate that the duplicate entry is not added
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject2")
        values = result.find(
            "fields", fullName="Type__c"
        ).valueSet.valueSetDefinition.value

        test_elem = list(v for v in values if v.fullName.text == "Outreach")
        assert len(test_elem) == 1

    def test_adds_values_second_object(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                "entries": [
                    {"fullName": "Test"},
                    {"fullName": "Foo", "label": "Bar", "default": True},
                ],
            },
        )

        # Validate that the second object has one picklist changed
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject2")
        values = result.find(
            "fields", fullName="Type__c"
        ).valueSet.valueSetDefinition.value

        test_elem = next(v for v in values if v.fullName.text == "Test")
        assert test_elem is not None
        assert test_elem.label.text == "Test"
        assert test_elem.default.text == "false"

        test_elem = next(v for v in values if v.fullName.text == "Foo")
        assert test_elem is not None
        assert test_elem.label.text == "Bar"
        assert test_elem.default.text == "true"

        test_elem = next(v for v in values if v.fullName.text == "Outreach")
        assert test_elem.default.text == "false"

        # Show that the other picklist is unaffected
        values = result.find(
            "fields", fullName="Time_Zone__c"
        ).valueSet.valueSetDefinition.value
        assert "Test" not in (v.fullName.text for v in values)

    def test_adds_record_type_entries(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                "entries": [
                    {"fullName": "Test"},
                    {"fullName": "Foo", "label": "Bar", "default": True},
                ],
                "record_types": ["*"],
            },
        )

        # Validate that the entries are added to the Record Type
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject2")

        for rt_name in ["Default_RT", "Second_RT"]:
            # Make sure we added the picklist values
            values = (
                result.find("recordTypes", fullName=rt_name)
                .find("picklistValues", picklist="Type__c")
                .values
            )
            assert "Test" in (v.fullName.text for v in values)
            assert "Foo" in (v.fullName.text for v in values)

            # Check that we set the default
            foo_value = next(v for v in values if v.fullName.text == "Foo")
            assert foo_value.default.text == "true"

            outreach_value = next(v for v in values if v.fullName.text == "Outreach")
            assert outreach_value.default.text == "false"

            # And that we did not add the other picklist's values
            values = (
                result.find("recordTypes", fullName=rt_name)
                .find("picklistValues", picklist="Time_Zone__c")
                .values
            )
            assert "Test" not in (v.fullName.text for v in values)

    def test_adds_record_type_entries__missing_picklist(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                "entries": [
                    {"fullName": "Test"},
                    {"fullName": "Foo", "label": "Bar", "default": True},
                ],
                "record_types": ["*"],
            },
        )

        # Validate that the entries are added to the Record Type
        # when the Record Type metadata doesn't already contain
        # an entry for this picklist
        tree = metadata_tree.fromstring(OBJECT_XML)
        tree.find("recordTypes", fullName="Default_RT").remove(
            tree.find("recordTypes", fullName="Default_RT").find(
                "picklistValues", picklist="Type__c"
            )
        )
        result = task._transform_entity(tree, "MyObject2")

        for rt_name in ["Default_RT", "Second_RT"]:
            # Make sure we added the picklist values
            values = (
                result.find("recordTypes", fullName=rt_name)
                .find("picklistValues", picklist="Type__c")
                .values
            )
            assert "Test" in (v.fullName.text for v in values)
            assert "Foo" in (v.fullName.text for v in values)

    def test_adds_record_type_entries__single(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                "entries": [
                    {"fullName": "Test"},
                    {"fullName": "Foo", "label": "Bar", "default": True},
                ],
                "record_types": ["Default_RT"],
            },
        )

        # Validate that the entries are added to the Record Type
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject2")

        values = (
            result.find("recordTypes", fullName="Default_RT")
            .find("picklistValues", picklist="Type__c")
            .values
        )
        assert "Test" in (v.fullName.text for v in values)
        assert "Foo" in (v.fullName.text for v in values)

        values = (
            result.find("recordTypes", fullName="Second_RT")
            .find("picklistValues", picklist="Type__c")
            .values
        )
        assert "Test" not in (v.fullName.text for v in values)

    def test_adds_record_type_entries__existing_quoted(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                "entries": [{"fullName": "Pacific%2FKiritimati"}],
                "record_types": ["Default_RT"],
            },
        )

        # Validate that the entries are not added to the Record Type in duplicate
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")

        values = (
            result.find("recordTypes", fullName="Default_RT")
            .find("picklistValues", picklist="Time_Zone__c")
            .values
        )
        assert "Pacific%2FKiritimati" in (v.fullName.text for v in values)
        assert "Pacific/Kiritimati" not in (v.fullName.text for v in values)

    def test_adds_record_type_entries__multiple(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                "entries": [
                    {"fullName": "Test"},
                    {"fullName": "Foo", "label": "Bar", "default": True},
                ],
                "record_types": ["Default_RT", "Second_RT"],
            },
        )

        # Validate that the entries are added to the Record Type
        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject2")

        for rt_name in ["Default_RT", "Second_RT"]:
            # Make sure we added the picklist values
            values = (
                result.find("recordTypes", fullName=rt_name)
                .find("picklistValues", picklist="Type__c")
                .values
            )
            assert "Test" in (v.fullName.text for v in values)
            assert "Foo" in (v.fullName.text for v in values)

    def test_add_before__existing(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                "entries": [
                    {"fullName": "Test", "add_before": "Pacific/Chatham"},
                    {"fullName": "Foo", "label": "Bar", "default": True},
                ],
                "record_types": ["Default_RT"],
            },
        )

        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        vsd = result.find("fields", fullName="Time_Zone__c").valueSet.valueSetDefinition
        values = vsd.value
        test_elem = next(v for v in values if v.fullName.text == "Test")
        assert vsd._element.index(test_elem._element) == 2  # The `sorted` element is 0

        test_elem = next(v for v in values if v.fullName.text == "Foo")
        assert vsd._element.index(test_elem._element) == 4

        rt_picklist = result.find("recordTypes", fullName="Default_RT").find(
            "picklistValues", picklist="Time_Zone__c"
        )
        rt_values = rt_picklist.values
        test_elem = next(v for v in rt_values if v.fullName.text == "Test")
        assert (
            rt_picklist._element.index(test_elem._element) == 2
        )  # The `picklist` element is 0
        test_elem = next(v for v in rt_values if v.fullName.text == "Foo")
        assert rt_picklist._element.index(test_elem._element) == 4

    def test_add_before__missing(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                "entries": [
                    {"fullName": "Test", "add_before": "Not-there"},
                    {"fullName": "Foo", "label": "Bar", "default": True},
                ],
                "record_types": ["Default_RT"],
            },
        )

        tree = metadata_tree.fromstring(OBJECT_XML)
        result = task._transform_entity(tree, "MyObject")
        vsd = result.find("fields", fullName="Time_Zone__c").valueSet.valueSetDefinition
        values = vsd.value
        test_elem = next(v for v in values if v.fullName.text == "Test")
        assert vsd._element.index(test_elem._element) == 3  # The `sorted` element is 0

        test_elem = next(v for v in values if v.fullName.text == "Foo")
        assert vsd._element.index(test_elem._element) == 4

        rt_picklist = result.find("recordTypes", fullName="Default_RT").find(
            "picklistValues", picklist="Time_Zone__c"
        )
        rt_values = rt_picklist.values
        test_elem = next(v for v in rt_values if v.fullName.text == "Test")
        assert (
            rt_picklist._element.index(test_elem._element) == 3
        )  # The `picklist` element is 0
        test_elem = next(v for v in rt_values if v.fullName.text == "Foo")
        assert rt_picklist._element.index(test_elem._element) == 4

    def test_init_options__old_api_version(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                AddPicklistEntries,
                {
                    "api_version": "35.0",
                    "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                    "entries": [{"fullName": "Test"}],
                },
            )

    def test_init_options__bad_api_version(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                AddPicklistEntries,
                {
                    "api_version": "35q.0",
                    "picklists": ["MyObject.Time_Zone__c", "MyObject2.Type__c"],
                    "entries": [{"fullName": "Test"}],
                },
            )

    def test_init_options__bad_picklist_name(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                AddPicklistEntries,
                {
                    "api_version": "47.0",
                    "picklists": ["MyObjectTime_Zone__c"],
                    "entries": [{"fullName": "Test"}],
                },
            )

    def test_init_options__standard_picklist_name(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                AddPicklistEntries,
                {
                    "api_version": "47.0",
                    "picklists": ["Opportunity.StageName"],
                    "entries": [{"fullName": "Test"}],
                },
            )

    def test_init_options__missing_fullname(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                AddPicklistEntries,
                {
                    "api_version": "47.0",
                    "picklists": ["Opportunity.Type__c"],
                    "entries": [{"label": "Test"}],
                },
            )

    def test_init_options__multiple_defaults(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                AddPicklistEntries,
                {
                    "api_version": "47.0",
                    "picklists": ["Opportunity.Type__c"],
                    "entries": [
                        {"fullName": "Test", "default": True},
                        {"fullName": "Bar", "default": True},
                    ],
                },
            )

    def test_raises_for_missing_picklist(self):
        task = create_task(
            AddPicklistEntries,
            {
                "api_version": "47.0",
                "picklists": ["MyObject.Type2__c"],
                "entries": [{"fullName": "Test", "default": True}],
            },
        )
        tree = metadata_tree.fromstring(OBJECT_XML)
        with pytest.raises(TaskOptionsError):
            task._transform_entity(tree, "MyObject")

    def test_raises_for_missing_picklists_option(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                AddPicklistEntries,
                {
                    "api_version": "47.0",
                    "entries": [{"fullName": "Test", "default": True}],
                },
            )

    def test_raises_for_global_value_set(self):
        with pytest.raises(TaskOptionsError):
            task = create_task(
                AddPicklistEntries,
                {
                    "api_version": "47.0",
                    "picklists": ["MyObject.TestGVS__c"],
                    "entries": [{"fullName": "Test", "default": True}],
                },
            )

            tree = metadata_tree.fromstring(OBJECT_XML)
            task._transform_entity(tree, "MyObject")
