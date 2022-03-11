import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl.layouts import (
    AddFieldsToPageLayout,
    AddRecordPlatformActionListItem,
    AddRelatedLists,
)
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.utils.xml import metadata_tree

MD = "{%s}" % metadata_tree.METADATA_NAMESPACE


LAYOUT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <layoutSections>
        <customLabel>false</customLabel>
        <detailHeading>false</detailHeading>
        <editHeading>true</editHeading>
        <label>Information</label>
        <layoutColumns>
            <layoutItems>
                <behavior>Readonly</behavior>
                <field>Name</field>
            </layoutItems>
        </layoutColumns>
        <layoutColumns/>
        <style>TwoColumnsTopToBottom</style>
    </layoutSections>
    {relatedLists}
</Layout>
"""

RELATED_LIST = """    <relatedLists>
        <fields>FULL_NAME</fields>
        <fields>CONTACT.TITLE</fields>
        <fields>CONTACT.EMAIL</fields>
        <fields>CONTACT.PHONE1</fields>
        <relatedList>RelatedContactList</relatedList>
    </relatedLists>
"""


class TestAddRelatedLists:
    def test_adds_related_list(self):
        task = create_task(
            AddRelatedLists,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "related_list": "TEST",
                "fields": "foo__c,bar__c",
            },
        )

        tree = metadata_tree.fromstring(
            LAYOUT_XML.format(relatedLists=RELATED_LIST).encode("utf-8")
        )
        element = tree._element

        assert len(element.findall(f".//{MD}relatedLists[{MD}relatedList='TEST']")) == 0

        task._transform_entity(tree, "Layout")

        assert len(element.findall(f".//{MD}relatedLists[{MD}relatedList='TEST']")) == 1
        field_elements = element.findall(
            f".//{MD}relatedLists[{MD}relatedList='TEST']/{MD}fields"
        )
        field_names = {elem.text for elem in field_elements}
        assert field_names == set(["foo__c", "bar__c"])

    def test_excludes_buttons(self):
        task = create_task(
            AddRelatedLists,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "related_list": "TEST",
                "fields": "foo__c,bar__c",
                "exclude_buttons": "New,Edit",
            },
        )

        tree = metadata_tree.fromstring(
            LAYOUT_XML.format(relatedLists=RELATED_LIST).encode("utf-8")
        )

        assert (
            len(tree._element.findall(f".//{MD}relatedLists[{MD}relatedList='TEST']"))
            == 0
        )

        result = task._transform_entity(tree, "Layout")

        assert (
            len(result._element.findall(f".//{MD}relatedLists[{MD}relatedList='TEST']"))
            == 1
        )
        button_elements = result._element.findall(
            f".//{MD}relatedLists[{MD}relatedList='TEST']/{MD}excludeButtons"
        )
        excluded_buttons = {elem.text for elem in button_elements}
        assert excluded_buttons == set(["New", "Edit"])

    def test_includes_buttons(self):
        task = create_task(
            AddRelatedLists,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "related_list": "TEST",
                "fields": "foo__c,bar__c",
                "custom_buttons": "MyCustomNewAction,MyCustomEditAction",
            },
        )

        tree = metadata_tree.fromstring(
            LAYOUT_XML.format(relatedLists=RELATED_LIST).encode("utf-8")
        )

        assert (
            len(tree._element.findall(f".//{MD}relatedLists[{MD}relatedList='TEST']"))
            == 0
        )

        result = task._transform_entity(tree, "Layout")
        element = result._element

        assert len(element.findall(f".//{MD}relatedLists[{MD}relatedList='TEST']")) == 1
        button_elements = element.findall(
            f".//{MD}relatedLists[{MD}relatedList='TEST']/{MD}customButtons"
        )
        custom_buttons = {elem.text for elem in button_elements}
        assert custom_buttons == set(["MyCustomNewAction", "MyCustomEditAction"])

    def test_adds_related_list_no_existing(self):
        task = create_task(
            AddRelatedLists,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "related_list": "TEST",
                "fields": "foo__c,bar__c",
            },
        )

        tree = metadata_tree.fromstring(
            LAYOUT_XML.format(relatedLists="").encode("utf-8")
        )
        element = tree._element

        assert len(element.findall(f".//{MD}relatedLists[{MD}relatedList='TEST']")) == 0

        task._transform_entity(tree, "Layout")

        assert len(element.findall(f".//{MD}relatedLists[{MD}relatedList='TEST']")) == 1
        field_elements = element.findall(
            f".//{MD}relatedLists[{MD}relatedList='TEST']/{MD}fields"
        )
        field_names = {elem.text for elem in field_elements}
        assert field_names == set(["foo__c", "bar__c"])

    def test_skips_existing_related_list(self):
        task = create_task(
            AddRelatedLists,
            {
                "managed": True,
                "api_version": "47.0",
                "api_names": "bar,foo",
                "related_list": "RelatedContactList",
                "fields": "foo__c,bar__c",
            },
        )

        tree = metadata_tree.fromstring(
            LAYOUT_XML.format(relatedLists=RELATED_LIST).encode("utf-8")
        )

        result = task._transform_entity(tree, "Layout")

        assert result is None


##### TestAddRecordPlatformActionListItem

# Mocked empty page layout (no action list)
#   Included common elements to better emulate a 'real' page layout.
MOCK_EMPTY_LAYOUT = """<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <excludeButtons>Submit</excludeButtons>
    <layoutSections>
        <customLabel>false</customLabel>
        <detailHeading>false</detailHeading>
        <editHeading>true</editHeading>
        <label>Information</label>
        <layoutColumns>
            <layoutItems>
                <behavior>Required</behavior>
                <field>Name</field>
            </layoutItems>
            <layoutItems>
                <emptySpace>true</emptySpace>
            </layoutItems>
            <layoutItems>
                <emptySpace>true</emptySpace>
            </layoutItems>
        </layoutColumns>
        <style>TwoColumnsTopToBottom</style>
    </layoutSections>
    <miniLayout>
        <fields>Name</fields>
        <relatedLists>
            <fields>NAME</fields>
            <fields>STATUS</fields>
            <relatedList>MOCKOBJECT</relatedList>
        </relatedLists>
    </miniLayout>
    <relatedLists>
        <fields>FULL_NAME</fields>
        <fields>CONTACT.TITLE</fields>
        <fields>CONTACT.EMAIL</fields>
        <fields>CONTACT.PHONE1</fields>
        <relatedList>RelatedContactList</relatedList>
    </relatedLists>
    <relatedLists>
        <relatedList>RelatedFileList</relatedList>
    </relatedLists>
    <showEmailCheckbox>false</showEmailCheckbox>
    <showHighlightsPanel>false</showHighlightsPanel>
    <showInteractionLogPanel>false</showInteractionLogPanel>
    <showRunAssignmentRulesCheckbox>false</showRunAssignmentRulesCheckbox>
    <showSubmitAndAttachButton>false</showSubmitAndAttachButton>
    {action_list_scenario}
</Layout>
"""

# Mocked existing action list
#   For different scenarios change action_list_context (Record, Listview, etc)
#   and the optional_first/last_action_items for inserting an existing item(s)
MOCK_EXISTING_ACTION_LIST = """
<platformActionList>
    <actionListContext>{action_list_context}</actionListContext>
    {optional_first_action_item}
    <platformActionListItems>
        <actionName>Edit</actionName>
        <actionType>StandardButton</actionType>
        <sortOrder>{}</sortOrder>
    </platformActionListItems>
    <platformActionListItems>
        <actionName>FeedItem.TextPost</actionName>
        <actionType>QuickAction</actionType>
        <sortOrder>{}</sortOrder>
    </platformActionListItems>
    {optional_last_action_item}
</platformActionList>
"""
# Empty action item and empty action list
EMPTY_ACTION_ITEM = """
    <platformActionListItems>
        <actionName>{action_name}</actionName>
        <actionType>{action_type}</actionType>
        <sortOrder>{expected_order}</sortOrder>
    </platformActionListItems>
"""
EMPTY_ACTION_LIST = """
<platformActionList>
    <actionListContext>{action_list_context}</actionListContext>
    {optional_action_item}
</platformActionList>
"""


class TestAddRecordPlatformActionListItem:
    def test_adds_action_item_to_existing_list_place_last(self):
        # options scenario:
        #   adding Quick Action to layout with existing action item list
        #   not setting place_first, so should be last in action list
        options = {
            "action_type": "QuickAction",
            "action_name": "pkg__mockObject.TestQuickAction",
        }
        task = create_task(AddRecordPlatformActionListItem, options)
        assert not task._place_first

        # Mocks: build our existing action list and create our metadata tree
        #   "Record" context
        #   default sort order (0, 1)
        #   no optional
        mock_action_list = MOCK_EXISTING_ACTION_LIST.format(
            0,
            1,
            action_list_context="Record",
            optional_first_action_item="",
            optional_last_action_item="",
        )
        metadata = metadata_tree.fromstring(
            MOCK_EMPTY_LAYOUT.format(action_list_scenario=mock_action_list).encode(
                "utf-8"
            )
        )
        mock_action_list_size = len(
            metadata._get_child("platformActionList").findall("platformActionListItems")
        )

        # Creating expected action item/list xml and metadata
        #   Expected context = "Record"
        #   The action_list_items <sortOrder> (positional *args) can be dynamically set from the mock_action_list_size or range
        #   using our optional_last_action_item to set our expected_action_item placement
        expected_action_item = EMPTY_ACTION_ITEM.format(
            expected_order=mock_action_list_size, **options
        )
        expected_action_list = MOCK_EXISTING_ACTION_LIST.format(
            *range(0, mock_action_list_size + 1),
            action_list_context="Record",
            optional_first_action_item="",
            optional_last_action_item=expected_action_item,
        )
        expected_metadata = metadata_tree.fromstring(
            MOCK_EMPTY_LAYOUT.format(action_list_scenario=expected_action_list).encode(
                "utf-8"
            )
        )

        # run test actual
        actual_metadata = task._transform_entity(metadata, "Layout")
        # Assert our transformed metadata is the same as our expected
        # This confirms, action list item size, sortOrder, and record context
        assert actual_metadata.tostring() == expected_metadata.tostring()

    def test_adds_action_item_to_existing_list_place_first(self):
        # options scenario:
        #   adding Quick Action to layout with existing Record context action item list
        #   place_first = true, so new action should end up first in action list
        options = {
            "action_type": "QuickAction",
            "action_name": "pkg__mockObject.TestQuickAction",
            "place_first": True,
        }
        task = create_task(AddRecordPlatformActionListItem, options)

        # Mocks: build our existing action list and create our metadata tree
        #   "Record" context
        #   default sort order (0, 1)
        #   no optional
        mock_action_list = MOCK_EXISTING_ACTION_LIST.format(
            0,
            1,
            action_list_context="Record",
            optional_first_action_item="",
            optional_last_action_item="",
        )
        metadata = metadata_tree.fromstring(
            MOCK_EMPTY_LAYOUT.format(action_list_scenario=mock_action_list).encode(
                "utf-8"
            )
        )
        mock_action_list_size = len(
            metadata._get_child("platformActionList").findall("platformActionListItems")
        )

        # Creating expected action item/list xml and metadata
        #   Expected context = "Record"
        #   our action_list_items <sortOrder> is being set dynamically from the mock_action_list_size (if we need to change later)
        #       setting our expected new action item to sortOrder 0 since placement should be first
        #   using our optional_first_action_item to set our expected_action_item
        expected_action_item = EMPTY_ACTION_ITEM.format(expected_order=0, **options)
        expected_action_list = MOCK_EXISTING_ACTION_LIST.format(
            *range(1, mock_action_list_size + 1),
            action_list_context="Record",
            optional_first_action_item=expected_action_item,
            optional_last_action_item="",
        )
        expected_metadata = metadata_tree.fromstring(
            MOCK_EMPTY_LAYOUT.format(action_list_scenario=expected_action_list).encode(
                "utf-8"
            )
        )

        # run test actual
        actual_metadata = task._transform_entity(metadata, "Layout")
        # Assert our transformed metadata is the same as our expected
        # This confirms, action list item size, sortOrder, and record context
        assert actual_metadata.tostring() == expected_metadata.tostring()

    def test_does_not_add_action_if_already_exists(self):
        # options scenario:
        #   attempting to add Quick Action to layout with quick action already existing
        options = {
            "action_type": "QuickAction",
            "action_name": "pkg__mockObject.TestQuickAction",
        }
        task = create_task(AddRecordPlatformActionListItem, options)

        # Mocks: build our existing action list and create our metadata tree
        #   "Record" context
        #   default sort order (0, 1)
        mock_action_item = EMPTY_ACTION_ITEM.format(expected_order=2, **options)
        mock_action_list = MOCK_EXISTING_ACTION_LIST.format(
            0,
            1,
            action_list_context="Record",
            optional_first_action_item="",
            optional_last_action_item=mock_action_item,
        )
        metadata = metadata_tree.fromstring(
            MOCK_EMPTY_LAYOUT.format(action_list_scenario=mock_action_list).encode(
                "utf-8"
            )
        )

        # run test
        actual_metadata = task._transform_entity(metadata, "Layout")
        # should not transform, and metadata should be none
        assert actual_metadata is None

    def test_creates_new_action_list_when_none_present(self):
        # options scenario:
        #   adding Quick Action to layout without existing action list
        #   place_first = true, so should be first in action list
        options = {
            "action_type": "QuickAction",
            "action_name": "pkg__mockObject.TestQuickAction",
            "place_first": True,
        }
        task = create_task(AddRecordPlatformActionListItem, options)

        # Mocks: build our existing action list and create our metadata tree
        #   This is an empty layout without any actionList
        metadata = metadata_tree.fromstring(
            MOCK_EMPTY_LAYOUT.format(action_list_scenario="").encode("utf-8")
        )

        # Creating expected action item/list xml and metadata
        #   Expected action list context  = "Record"
        #   Should only contain one action item, specified in options
        expected_action_item = EMPTY_ACTION_ITEM.format(expected_order=0, **options)
        expected_action_list = EMPTY_ACTION_LIST.format(
            action_list_context="Record", optional_action_item=expected_action_item
        )
        expected_metadata = metadata_tree.fromstring(
            MOCK_EMPTY_LAYOUT.format(action_list_scenario=expected_action_list).encode(
                "utf-8"
            )
        )

        # run test actual
        actual_metadata = task._transform_entity(metadata, "Layout")
        # Assert our transformed metadata is the same as our expected
        # This confirms, action list item size, sortOrder, and record context
        assert actual_metadata.tostring() == expected_metadata.tostring()

    def test_adds_new_action_list_when_existing_list_is_not_record_context(self):
        # options scenario:
        #   adding Quick Action to layout with existing action item list
        options = {
            "action_type": "QuickAction",
            "action_name": "pkg__mockObject.TestQuickAction",
        }
        task = create_task(AddRecordPlatformActionListItem, options)

        # Mocks: build our existing action list and create our metadata tree
        #   "Listview" context (which should trigger creation of new)
        #   default sort order (0, 1)
        #   no additional action items.
        mock_action_list = MOCK_EXISTING_ACTION_LIST.format(
            0,
            1,
            action_list_context="Listview",
            optional_first_action_item="",
            optional_last_action_item="",
        )
        metadata = metadata_tree.fromstring(
            MOCK_EMPTY_LAYOUT.format(action_list_scenario=mock_action_list).encode(
                "utf-8"
            )
        )

        # Creating expected action item/list xml and metadata
        #   Our expected metadata includes both the mock_action_list with context "Listview",
        #       and an actionList of context "Record" created during the transform
        #   our action_list_items <sortOrder> is being set dynamically from the mock_action_list_size (if we need to change later)
        #       setting our added item to 0 sortOrder since only item
        #       using option_action_item to set expected action item
        expected_action_item = EMPTY_ACTION_ITEM.format(expected_order=0, **options)
        expected_action_list = EMPTY_ACTION_LIST.format(
            action_list_context="Record", optional_action_item=expected_action_item
        )
        expected_metadata = metadata_tree.fromstring(
            MOCK_EMPTY_LAYOUT.format(
                action_list_scenario=str(mock_action_list + "\n" + expected_action_list)
            ).encode("utf-8")
        )
        # run test actual
        actual_metadata = task._transform_entity(metadata, "Layout")
        # Assert our transformed metadata is the same as our expected
        # This confirms, action list item size, sortOrder, and record context
        assert actual_metadata.tostring() == expected_metadata.tostring()


# Mocked empty page layout
MOCK_ADD_FIELDS_LAYOUT = """<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <excludeButtons>Submit</excludeButtons>
    <layoutSections>
        <customLabel>false</customLabel>
        <detailHeading>false</detailHeading>
        <editHeading>true</editHeading>
        <label>Information</label>
        <layoutColumns>
            <layoutItems>
                <behavior>Required</behavior>
                <field>Name</field>
            </layoutItems>
            <layoutItems>
                <emptySpace>true</emptySpace>
            </layoutItems>
            <layoutItems>
                <emptySpace>true</emptySpace>
            </layoutItems>
        </layoutColumns>
        <layoutColumns>
            <layoutItems>
                <emptySpace>true</emptySpace>
            </layoutItems>
            <layoutItems>
                <emptySpace>true</emptySpace>
            </layoutItems>
        </layoutColumns>
        <style>TwoColumnsTopToBottom</style>
    </layoutSections>
    <layoutSections>
        <customLabel>false</customLabel>
        <detailHeading>false</detailHeading>
        <editHeading>true</editHeading>
        <label>Address Information</label>
        <layoutColumns>
            <layoutItems>
                <behavior>Edit</behavior>
                <field>BillingAddress</field>
            </layoutItems>
        </layoutColumns>
        <layoutColumns>
            <layoutItems>
                <behavior>Edit</behavior>
                <field>ShippingAddress</field>
            </layoutItems>
        </layoutColumns>
        <style>TwoColumnsTopToBottom</style>
    </layoutSections>
    <relatedLists>
        <fields>FULL_NAME</fields>
        <fields>CONTACT.TITLE</fields>
        <fields>CONTACT.EMAIL</fields>
        <fields>CONTACT.PHONE1</fields>
        <relatedList>RelatedContactList</relatedList>
    </relatedLists>
</Layout>
"""


class TestAddFieldsToPageLayout:
    def test_add_fields_positioning(self):
        """Testing the positioning keywords [top|bottom|before|after]"""
        task = create_task(
            AddFieldsToPageLayout,
            {
                "api_names": "Account-Account Layout",
                "fields": [
                    {
                        "api_name": "After",
                        "position": [
                            {
                                "relative": "after",
                                "field": "Name",
                            },
                        ],
                    },
                    {
                        "api_name": "Before",
                        "position": [
                            {
                                "relative": "before",
                                "field": "Name",
                            },
                        ],
                    },
                    {
                        "api_name": "Bottom",
                        "position": [
                            {
                                "relative": "bottom",
                                "column": "first",
                                "section": 0,
                            },
                        ],
                    },
                    {
                        "api_name": "Top",
                        "position": [
                            {
                                "relative": "top",
                                "column": "last",
                                "section": 0,
                            },
                        ],
                    },
                ],
            },
        )
        tree = metadata_tree.fromstring(MOCK_ADD_FIELDS_LAYOUT.format().encode("utf-8"))
        result = task._transform_entity(tree, "Layout")

        element = result._element
        updated_sections = element.findall(f".//{MD}layoutSections")
        items = updated_sections[0].findall(f".//{MD}layoutItems")

        assert items[0].getchildren()[1].text == "Before"
        assert items[2].getchildren()[1].text == "After"
        assert items[5].getchildren()[1].text == "Bottom"
        assert items[6].getchildren()[1].text == "Top"

    def test_add_fields_default_positioning(self):
        """Making sure the default column position is applied if not supplied"""
        task = create_task(
            AddFieldsToPageLayout,
            {
                "api_names": "Account-Account Layout",
                "fields": [
                    {
                        "api_name": "Industry",
                    },
                ],
            },
        )
        tree = metadata_tree.fromstring(MOCK_ADD_FIELDS_LAYOUT.format().encode("utf-8"))
        result = task._transform_entity(tree, "Layout")

        element = result._element
        updated_sections = element.findall(f".//{MD}layoutSections")
        cols = updated_sections[0].findall(f".//{MD}layoutColumns")
        items = cols[1].findall(f".//{MD}layoutItems")
        assert items[0].getchildren()[1].text == "Industry"

    def test_add_fields_adding_pages(self):
        """Testing of adding Visualforce pages and making sure their options are applied"""
        task = create_task(
            AddFieldsToPageLayout,
            {
                "api_names": "Account-Account Layout",
                "pages": [
                    {
                        "api_name": "TestPage2",
                        "height": "500",
                        "show_label": True,
                        "show_scrollbars": True,
                        "width": "50%",
                    },
                    {
                        "api_name": "TestPage",
                    },
                ],
            },
        )
        tree = metadata_tree.fromstring(MOCK_ADD_FIELDS_LAYOUT.format().encode("utf-8"))
        result = task._transform_entity(tree, "Layout")

        element = result._element
        updated_sections = element.findall(f".//{MD}layoutSections")
        cols = updated_sections[0].findall(f".//{MD}layoutColumns")
        items = cols[1].findall(f".//{MD}layoutItems")
        # {http://soap.sforce.com/2006/04/metadata}page
        assert "page" in items[0].getchildren()[0].tag  # Its a page!!!
        assert items[0].getchildren()[0].text == "TestPage"

        # Check defaults are applied
        assert items[0].getchildren()[1].text == "200"  # height
        assert items[0].getchildren()[2].text == "false"  # showLabel
        assert items[0].getchildren()[3].text == "false"  # showScrollbars
        assert items[0].getchildren()[4].text == "100%"  # width

        assert items[1].getchildren()[0].text == "TestPage2"
        # Check options
        assert items[1].getchildren()[1].text == "500"  # height
        assert items[1].getchildren()[2].text == "true"  # showLabel
        assert items[1].getchildren()[3].text == "true"  # showScrollbars
        assert items[1].getchildren()[4].text == "50%"  # width

    def test_add_fields_skip_existing(self):
        """Make sure if a field is skipped if it already exists in the layout"""
        task = create_task(
            AddFieldsToPageLayout,
            {
                "api_names": "Account-Account Layout",
                "fields": [
                    {
                        "api_name": "Name",
                        "position": [
                            {"relative": "before", "field": "Name"},
                        ],
                    },
                ],
            },
        )
        tree = metadata_tree.fromstring(MOCK_ADD_FIELDS_LAYOUT.format().encode("utf-8"))
        result = task._transform_entity(tree, "Layout")

        element = result._element
        updated_sections = element.findall(f".//{MD}layoutSections")
        items = updated_sections[0].findall(f".//{MD}layoutItems")
        assert len(items) == 5

    def test_add_fields_fallback(self):
        """Testing the fallback procedure of the positioning, in the order listed each item of
        the list is tried, and if not successful the default is finally applied."""
        task = create_task(
            AddFieldsToPageLayout,
            {
                "api_names": "Account-Account Layout",
                "fields": [
                    {
                        "api_name": "Lost",
                        "position": [
                            {"relative": "before", "field": "NotFound"},
                            {"relative": "before", "field": "NotFound2"},
                            {"relative": "top", "section": 2, "column": "last"},
                        ],
                    },
                ],
            },
        )
        tree = metadata_tree.fromstring(MOCK_ADD_FIELDS_LAYOUT.format().encode("utf-8"))
        result = task._transform_entity(tree, "Layout")

        element = result._element
        sections = element.findall(f".//{MD}layoutSections")
        cols = sections[0].findall(f".//{MD}layoutColumns")
        items = cols[1].findall(f".//{MD}layoutItems")

        assert len(items) == 3  # Field Still Added
        # Field Added at top of last column
        assert items[0].getchildren()[1].text == "Lost"

    def test_add_fields_behavior(self):
        """Testing the application of field behavior. Edit is the default and
        'required' or 'read_only' are alternative options"""
        task = create_task(
            AddFieldsToPageLayout,
            {
                "api_names": "Account-Account Layout",
                "fields": [
                    {
                        "api_name": "Edit",
                        "position": [
                            {"relative": "top", "section": 0, "column": "first"},
                        ],
                    },
                    {
                        "api_name": "Required",
                        "required": True,
                        "position": [
                            {"relative": "top", "section": 0, "column": "first"},
                        ],
                    },
                    {
                        "api_name": "Readonly",
                        "read_only": True,
                        "position": [
                            {"relative": "top", "section": 0, "column": "first"},
                        ],
                    },
                ],
            },
        )
        tree = metadata_tree.fromstring(MOCK_ADD_FIELDS_LAYOUT.format().encode("utf-8"))
        result = task._transform_entity(tree, "Layout")

        element = result._element
        sections = element.findall(f".//{MD}layoutSections")
        cols = sections[0].findall(f".//{MD}layoutColumns")
        items = cols[0].findall(f".//{MD}layoutItems")

        # Fields display in reverse order than they were listed
        assert items[0].getchildren()[0].text == "Readonly"
        assert items[1].getchildren()[0].text == "Required"
        assert items[2].getchildren()[0].text == "Edit"

    def test_add_fields_required_readonly(self):
        """required and read_only are mutually exclusive"""
        task = create_task(
            AddFieldsToPageLayout,
            {
                "api_names": "Account-Account Layout",
                "fields": [
                    {
                        "api_name": "NotAdded",
                        "required": True,
                        "read_only": True,
                    },
                ],
            },
        )
        tree = metadata_tree.fromstring(MOCK_ADD_FIELDS_LAYOUT.format().encode("utf-8"))

        with pytest.raises(TaskOptionsError):
            task._transform_entity(tree, "Layout")

    def test_add_fields_position_type_column(self):
        """Check positioning root validators column relative"""

        with pytest.raises(ValueError):
            create_task(
                AddFieldsToPageLayout,
                {
                    "api_names": "Account-Account Layout",
                    "fields": [
                        {
                            "api_name": "Top",
                            "position": [
                                {
                                    "field": "Name",
                                    "relative": "top",
                                    "column": "last",
                                    "section": 0,
                                },
                            ],
                        },
                    ],
                },
            )

    def test_add_fields_position_type_field(self):
        """Check positioning root validators field relative"""

        with pytest.raises(ValueError):
            create_task(
                AddFieldsToPageLayout,
                {
                    "api_names": "Account-Account Layout",
                    "fields": [
                        {
                            "api_name": "After",
                            "position": [
                                {
                                    "field": "Name",
                                    "relative": "after",
                                    "column": "last",
                                    "section": 0,
                                },
                            ],
                        },
                    ],
                },
            )
