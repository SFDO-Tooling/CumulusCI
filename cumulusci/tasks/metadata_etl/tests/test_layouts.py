import unittest  # add action
from unittest.mock import Mock, call, PropertyMock  # add action

from cumulusci.tasks.salesforce.tests.util import create_task

from tasks.metadata_etl import (
    InsertChildInMetadataSingleEntityTransformTask,
)  # add action
from cumulusci.tasks.metadata_etl.layouts import (
    InsertRecordPlatformActionListItem,
)  # add action

from cumulusci.tasks.metadata_etl import AddRelatedLists
from cumulusci.utils.xml import metadata_tree
from cumulusci.utils.xml.metadata_tree import MetadataElement, fromstring  # add action
from cumulusci.core.exceptions import CumulusCIException  # add action

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


##### Lightning Action add to Layout tests
class UnitTestInsertRecordPlatformActionListItem(unittest.TestCase):
    def test_entity(self):
        self.assertEqual("Layout", InsertRecordPlatformActionListItem.entity)

    def test_init_options(self):
        for index, scenario in enumerate(
            [
                # managed: False
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": None,
                        "namespace_inject": "namespace",
                        "managed": False,
                    },
                    "expected": {
                        "_action_type": "action_type",
                        "_action_name": "action_name",
                        "_neighbor_action_type": None,
                        "_neighbor_action_name": None,
                    },
                },
                {
                    "options": {
                        "action_type": "%%%NAMESPACE%%%action_type",
                        "action_name": "%%%NAMESPACE%%%action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": None,
                        "namespace_inject": "namespace",
                        "managed": False,
                    },
                    "expected": {
                        "_action_type": "%%%NAMESPACE%%%action_type",
                        "_action_name": "action_name",
                        "_neighbor_action_type": None,
                        "_neighbor_action_name": None,
                    },
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": "neighbor_action_type",
                        "neighbor_action_name": "neighbor_action_name",
                        "namespace_inject": "namespace",
                        "managed": False,
                    },
                    "expected": {
                        "_action_type": "action_type",
                        "_action_name": "action_name",
                        "_neighbor_action_type": "neighbor_action_type",
                        "_neighbor_action_name": "neighbor_action_name",
                    },
                },
                {
                    "options": {
                        "action_type": "%%%NAMESPACE%%%action_type",
                        "action_name": "%%%NAMESPACE%%%action_name",
                        "neighbor_action_type": "%%%NAMESPACE%%%neighbor_action_type",
                        "neighbor_action_name": "%%%NAMESPACE%%%neighbor_action_name",
                        "namespace_inject": "namespace",
                        "managed": False,
                    },
                    "expected": {
                        "_action_type": "%%%NAMESPACE%%%action_type",
                        "_action_name": "action_name",
                        "_neighbor_action_type": "%%%NAMESPACE%%%neighbor_action_type",
                        "_neighbor_action_name": "neighbor_action_name",
                    },
                },
                # managed: True
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": None,
                        "namespace_inject": "namespace",
                        "managed": True,
                    },
                    "expected": {
                        "_action_type": "action_type",
                        "_action_name": "action_name",
                        "_neighbor_action_type": None,
                        "_neighbor_action_name": None,
                    },
                },
                {
                    "options": {
                        "action_type": "%%%NAMESPACE%%%action_type",
                        "action_name": "%%%NAMESPACE%%%action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": None,
                        "namespace_inject": "namespace",
                        "managed": True,
                    },
                    "expected": {
                        "_action_type": "%%%NAMESPACE%%%action_type",
                        "_action_name": "namespace__action_name",
                        "_neighbor_action_type": None,
                        "_neighbor_action_name": None,
                    },
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": "neighbor_action_type",
                        "neighbor_action_name": "neighbor_action_name",
                        "namespace_inject": "namespace",
                        "managed": True,
                    },
                    "expected": {
                        "_action_type": "action_type",
                        "_action_name": "action_name",
                        "_neighbor_action_type": "neighbor_action_type",
                        "_neighbor_action_name": "neighbor_action_name",
                    },
                },
                {
                    "options": {
                        "action_type": "%%%NAMESPACE%%%action_type",
                        "action_name": "%%%NAMESPACE%%%action_name",
                        "neighbor_action_type": "%%%NAMESPACE%%%neighbor_action_type",
                        "neighbor_action_name": "%%%NAMESPACE%%%neighbor_action_name",
                        "namespace_inject": "namespace",
                        "managed": True,
                    },
                    "expected": {
                        "_action_type": "%%%NAMESPACE%%%action_type",
                        "_action_name": "namespace__action_name",
                        "_neighbor_action_type": "%%%NAMESPACE%%%neighbor_action_type",
                        "_neighbor_action_name": "namespace__neighbor_action_name",
                    },
                },
            ]
        ):
            options = scenario["options"]
            task = create_task(InsertRecordPlatformActionListItem, options)

            self.assertEqual(
                scenario["expected"]["_action_type"],
                task._action_type,
                f"index: {index}",
            )
            self.assertEqual(
                scenario["expected"]["_action_name"],
                task._action_name,
                f"index: {index}",
            )
            self.assertEqual(
                scenario["expected"]["_neighbor_action_type"],
                task._neighbor_action_type,
                f"index: {index}",
            )
            self.assertEqual(
                scenario["expected"]["_neighbor_action_name"],
                task._neighbor_action_name,
                f"index: {index}",
            )

    def test_is_targeted_child(self):
        # For each option/scenario to setup
        for index, scenario in enumerate(
            [
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                    },
                    "child": {
                        "actionType": "action_type",
                        "actionName": "action_name",
                    },
                    "expected": True,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                    },
                    "child": {
                        "actionType": "is not action_type",
                        "actionName": "action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                    },
                    "child": {
                        "actionType": "action_type",
                        "actionName": "is not action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                    },
                    "child": {
                        "actionType": "is not action_type",
                        "actionName": "is not action_name",
                    },
                    "expected": False,
                },
            ]
        ):
            task = create_task(InsertRecordPlatformActionListItem, scenario["options"])

            # Assert task attributes are set as expected by _init_options.
            self.assertEqual(
                scenario["options"]["action_type"], task._action_type, f"index: {index}"
            )
            self.assertEqual(
                scenario["options"]["action_name"], task._action_name, f"index: {index}"
            )

            child = Mock(spec=MetadataElement)

            child.actionType = Mock()
            child.actionType.text = scenario["child"]["actionType"]

            child.actionName = Mock()
            child.actionName.text = scenario["child"]["actionName"]

            # Execute test
            actual = task._is_targeted_child(child)

            # Assert
            self.assertEqual(scenario["expected"], actual, f"index: {index}")

    def test_is_targeted_child_neighbor(self):
        for index, scenario in enumerate(
            [
                # neighbor_action_type is None and neighbor_action_name is None
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": None,
                    },
                    "child": {
                        "actionType": "neighbor_action_type",
                        "actionName": "neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": None,
                    },
                    "child": {
                        "actionType": "is not neighbor_action_type",
                        "actionName": "neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": None,
                    },
                    "child": {
                        "actionType": "neighbor_action_type",
                        "actionName": "is not neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": None,
                    },
                    "child": {
                        "actionType": "is not neighbor_action_type",
                        "actionName": "is not neighbor_action_name",
                    },
                    "expected": False,
                },
                # neighbor_action_type is not None and neighbor_action_name is None
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": "neighbor_action_type",
                        "neighbor_action_name": None,
                    },
                    "child": {
                        "actionType": "neighbor_action_type",
                        "actionName": "neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": "neighbor_action_type",
                        "neighbor_action_name": None,
                    },
                    "child": {
                        "actionType": "is not neighbor_action_type",
                        "actionName": "neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": "neighbor_action_type",
                        "neighbor_action_name": None,
                    },
                    "child": {
                        "actionType": "neighbor_action_type",
                        "actionName": "is not neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": "neighbor_action_type",
                        "neighbor_action_name": None,
                    },
                    "child": {
                        "actionType": "is not neighbor_action_type",
                        "actionName": "is not neighbor_action_name",
                    },
                    "expected": False,
                },
                # neighbor_action_type is None and neighbor_action_name is not None
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": "neighbor_action_name",
                    },
                    "child": {
                        "actionType": "neighbor_action_type",
                        "actionName": "neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": "neighbor_action_name",
                    },
                    "child": {
                        "actionType": "is not neighbor_action_type",
                        "actionName": "neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": "neighbor_action_name",
                    },
                    "child": {
                        "actionType": "neighbor_action_type",
                        "actionName": "is not neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": None,
                        "neighbor_action_name": "neighbor_action_name",
                    },
                    "child": {
                        "actionType": "is not neighbor_action_type",
                        "actionName": "is not neighbor_action_name",
                    },
                    "expected": False,
                },
                # neighbor_action_type is not None and neighbor_action_name is not None
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": "neighbor_action_type",
                        "neighbor_action_name": "neighbor_action_name",
                    },
                    "child": {
                        "actionType": "neighbor_action_type",
                        "actionName": "neighbor_action_name",
                    },
                    "expected": True,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": "neighbor_action_type",
                        "neighbor_action_name": "neighbor_action_name",
                    },
                    "child": {
                        "actionType": "is not neighbor_action_type",
                        "actionName": "neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": "neighbor_action_type",
                        "neighbor_action_name": "neighbor_action_name",
                    },
                    "child": {
                        "actionType": "neighbor_action_type",
                        "actionName": "is not neighbor_action_name",
                    },
                    "expected": False,
                },
                {
                    "options": {
                        "action_type": "action_type",
                        "action_name": "action_name",
                        "neighbor_action_type": "neighbor_action_type",
                        "neighbor_action_name": "neighbor_action_name",
                    },
                    "child": {
                        "actionType": "is not neighbor_action_type",
                        "actionName": "is not neighbor_action_name",
                    },
                    "expected": False,
                },
            ]
        ):
            task = create_task(InsertRecordPlatformActionListItem, scenario["options"])

            # Assert task attributes are set as expected by _init_options.
            self.assertEqual(
                scenario["options"]["neighbor_action_type"],
                task._neighbor_action_type,
                f"index: {index}",
            )
            self.assertEqual(
                scenario["options"]["neighbor_action_name"],
                task._neighbor_action_name,
                f"index: {index}",
            )

            child = Mock(spec=MetadataElement)

            child.actionType = Mock()
            child.actionType.text = scenario["child"]["actionType"]

            child.actionName = Mock()
            child.actionName.text = scenario["child"]["actionName"]

            # Execute test
            actual = task._is_targeted_child_neighbor(child)

            # Assert
            self.assertEqual(
                scenario["expected"], actual, f"index: {index}",
            )

    def test_populate_targeted_child(self):
        for index, options in enumerate(
            [
                {"action_type": "action_type", "action_name": "action_name"},
                {"action_type": "action_typezzz", "action_name": "action_name"},
                {"action_type": "action_type", "action_name": "action_namezzz"},
            ]
        ):
            action_type = options["action_type"]
            action_name = options["action_name"]

            child = Mock(spec=MetadataElement)
            child.append = Mock()

            task = create_task(InsertRecordPlatformActionListItem, options)

            # Assert task attributes are set as expected by _init_options.
            self.assertEqual(action_type, task._action_type, f"index: {index}")
            self.assertEqual(action_name, task._action_name, f"index: {index}")

            child.append.expected_calls = [
                call("actionName", task._action_name),
                call("actionType", task._action_type),
            ]

            # Execute test
            task._populate_targeted_child(child)

            # Assert
            child.append.assert_has_calls(child.append.expected_calls)

    def test_update_platform_action_list_items_sort_order(self):
        # child_0 finds a sortOrder
        child_0 = Mock(spec=MetadataElement)

        child_0__sortOrder = Mock(spec=MetadataElement)
        child_0__sortOrder__text = PropertyMock()
        type(child_0__sortOrder).text = child_0__sortOrder__text

        child_0.find = Mock(return_value=child_0__sortOrder)
        self.assertTrue(child_0.find.return_value)
        child_0.append = Mock(
            side_effect=CumulusCIException("child_0.sortOrder already exists")
        )

        # child_1 does not find a sortOrder
        child_1 = Mock(spec=MetadataElement)

        child_1__sortOrder = Mock(spec=MetadataElement)
        child_1__sortOrder__text = PropertyMock()
        type(child_1__sortOrder).text = child_1__sortOrder__text

        child_1.find = Mock(return_value=None)
        self.assertFalse(child_1.find.return_value)
        child_1.append = Mock(return_value=child_1__sortOrder)

        # child_2 does not find a sortOrder
        child_2 = Mock(spec=MetadataElement)

        child_2__sortOrder = Mock(spec=MetadataElement)
        child_2__sortOrder__text = PropertyMock(return_value="99")
        type(child_2__sortOrder).text = child_2__sortOrder__text

        child_2.find = Mock(return_value=None)
        self.assertFalse(child_2.find.return_value)
        child_2.append = Mock(return_value=child_2__sortOrder)

        # child_3 finds a sortOrder
        child_3 = Mock(spec=MetadataElement)

        child_3__sortOrder = Mock(spec=MetadataElement)
        child_3__sortOrder__text = PropertyMock()
        type(child_3__sortOrder).text = child_3__sortOrder__text

        child_3.find = Mock(return_value=child_3__sortOrder)
        self.assertTrue(child_3.find.return_value)
        child_3.append = Mock(
            side_effect=CumulusCIException("child_3.sortOrder already exists")
        )

        children = [
            child_0,
            child_1,
            child_2,
            child_3,
        ]

        platform_action_list = Mock(spec=MetadataElement)
        platform_action_list.findall = Mock(return_value=children)

        task = create_task(
            InsertRecordPlatformActionListItem,
            {"action_type": "action_type", "action_name": "action_name"},
        )

        # Execute test
        task._update_platform_action_list_items_sort_order(platform_action_list)

        # Assert
        platform_action_list.findall.assert_called_once_with("platformActionListItems")

        child_0.find.assert_called_once_with("sortOrder")
        child_0.append.assert_not_called()
        child_0__sortOrder__text.assert_called_once_with("0")

        child_1.find.assert_called_once_with("sortOrder")
        child_1.append.assert_called_once_with("sortOrder")
        child_1__sortOrder__text.assert_called_once_with("1")

        child_2.find.assert_called_once_with("sortOrder")
        child_2.append.assert_called_once_with("sortOrder")
        child_2__sortOrder__text.assert_called_once_with("2")

        child_3.find.assert_called_once_with("sortOrder")
        child_3.append.assert_not_called()
        child_3__sortOrder__text.assert_called_once_with("3")

    def test_transform_entity__metadata_modified__children_not_found(self):
        record_platform_action_list = Mock(spec=MetadataElement)
        record_platform_action_list.append = Mock()

        metadata = Mock(spec=MetadataElement)

        metadata.find = Mock(return_value=None)
        self.assertFalse(metadata.find.return_value)

        metadata.append = Mock(return_value=record_platform_action_list)

        api_name = "api_name"

        task = create_task(
            InsertRecordPlatformActionListItem,
            {"action_type": "action_type", "action_name": "action_name"},
        )

        task.logger.info = Mock()

        task._insert_targeted_child_in_parent = Mock(return_value=True)
        self.assertTrue(task._insert_targeted_child_in_parent.return_value)

        task._update_platform_action_list_items_sort_order = Mock()

        expected_logger_info_calls = [
            call(f'Appending platformActionListItems for layout "{api_name}"'),
            call(""),
        ]

        expected = metadata

        # Execute test
        actual = task._transform_entity(metadata, api_name)

        # Assert
        metadata.find.assert_called_once_with(
            "platformActionList", actionListContext="Record"
        )

        metadata.append.assert_called_once_with("platformActionList")
        record_platform_action_list.append.assert_called_once_with(
            "actionListContext", text="Record"
        )

        task.logger.info.assert_has_calls(expected_logger_info_calls)

        task._insert_targeted_child_in_parent.assert_called_once_with(
            record_platform_action_list, "platformActionListItems"
        )

        task._update_platform_action_list_items_sort_order.assert_called_once_with(
            record_platform_action_list
        )

        self.assertEqual(expected, actual)

    def test_transform_entity__metadata_modified__children_found(self):
        record_platform_action_list = Mock(spec=MetadataElement)
        record_platform_action_list.append = Mock()

        metadata = Mock(spec=MetadataElement)

        metadata.find = Mock(return_value=None)
        self.assertFalse(metadata.find.return_value)

        metadata.append = Mock(return_value=record_platform_action_list)

        api_name = "api_name"

        task = create_task(
            InsertRecordPlatformActionListItem,
            {"action_type": "action_type", "action_name": "action_name"},
        )

        task.logger.info = Mock()

        task._insert_targeted_child_in_parent = Mock(return_value=True)
        self.assertTrue(task._insert_targeted_child_in_parent.return_value)

        task._update_platform_action_list_items_sort_order = Mock()

        expected_logger_info_calls = [
            call(f'Appending platformActionListItems for layout "{api_name}"'),
            call(""),
        ]

        expected = metadata

        # Execute test
        actual = task._transform_entity(metadata, api_name)

        # Assert
        metadata.find.assert_called_once_with(
            "platformActionList", actionListContext="Record"
        )

        metadata.append.assert_called_once_with("platformActionList")
        record_platform_action_list.append.assert_called_once_with(
            "actionListContext", text="Record"
        )

        task.logger.info.assert_has_calls(expected_logger_info_calls)

        task._insert_targeted_child_in_parent.assert_called_once_with(
            record_platform_action_list, "platformActionListItems"
        )

        task._update_platform_action_list_items_sort_order.assert_called_once_with(
            record_platform_action_list
        )

        self.assertEqual(expected, actual)

    def test_transform_entity__metadata_not_modified__children_not_found(self):
        record_platform_action_list = Mock(spec=MetadataElement)
        record_platform_action_list.append = Mock()

        metadata = Mock(spec=MetadataElement)

        metadata.find = Mock(return_value=None)
        self.assertFalse(metadata.find.return_value)

        metadata.append = Mock(return_value=record_platform_action_list)

        api_name = "api_name"

        task = create_task(
            InsertRecordPlatformActionListItem,
            {"action_type": "action_type", "action_name": "action_name"},
        )

        task.logger.info = Mock()

        task._insert_targeted_child_in_parent = Mock(return_value=False)
        self.assertFalse(task._insert_targeted_child_in_parent.return_value)

        task._update_platform_action_list_items_sort_order = Mock()

        expected_logger_info_calls = [
            call(f'Appending platformActionListItems for layout "{api_name}"'),
            call(""),
        ]

        expected = None

        # Execute test
        actual = task._transform_entity(metadata, api_name)

        # Assert
        metadata.find.assert_called_once_with(
            "platformActionList", actionListContext="Record"
        )

        metadata.append.assert_called_once_with("platformActionList")
        record_platform_action_list.append.assert_called_once_with(
            "actionListContext", text="Record"
        )

        task.logger.info.assert_has_calls(expected_logger_info_calls)

        task._insert_targeted_child_in_parent.assert_called_once_with(
            record_platform_action_list, "platformActionListItems"
        )

        task._update_platform_action_list_items_sort_order.assert_not_called()

        self.assertEqual(expected, actual)

    def test_transform_entity__metadata_not_modified__children_found(self):
        record_platform_action_list = Mock(spec=MetadataElement)
        record_platform_action_list.append = Mock()

        metadata = Mock(spec=MetadataElement)

        metadata.find = Mock(return_value=None)
        self.assertFalse(metadata.find.return_value)

        metadata.append = Mock(return_value=record_platform_action_list)

        api_name = "api_name"

        task = create_task(
            InsertRecordPlatformActionListItem,
            {"action_type": "action_type", "action_name": "action_name"},
        )

        task.logger.info = Mock()

        task._insert_targeted_child_in_parent = Mock(return_value=False)
        self.assertFalse(task._insert_targeted_child_in_parent.return_value)

        task._update_platform_action_list_items_sort_order = Mock()

        expected_logger_info_calls = [
            call(f'Appending platformActionListItems for layout "{api_name}"'),
            call(""),
        ]

        expected = None

        # Execute test
        actual = task._transform_entity(metadata, api_name)

        # Assert
        metadata.find.assert_called_once_with(
            "platformActionList", actionListContext="Record"
        )

        metadata.append.assert_called_once_with("platformActionList")
        record_platform_action_list.append.assert_called_once_with(
            "actionListContext", text="Record"
        )

        task.logger.info.assert_has_calls(expected_logger_info_calls)

        task._insert_targeted_child_in_parent.assert_called_once_with(
            record_platform_action_list, "platformActionListItems"
        )

        task._update_platform_action_list_items_sort_order.assert_not_called()

        self.assertEqual(expected, actual)


class FunctionalTestInsertRecordPlatformActionListItem(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        super().setUp()

        self.api_name = "api_name"
        self.action_type = "action_type"
        self.action_name = "action_name"
        self.neighbor_action_type = "neighbor_action_type"
        self.neighbor_action_name = "neighbor_action_name"

    def test_transform_entity__parent_not_found(self):

        METADATA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
</Layout>
"""

        EXPECTED_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = fromstring(EXPECTED_XML.encode("utf-8"))

        for options in [
            # Place at original index if exists else at the end
            {"action_name": self.action_name, "action_type": self.action_type},
            # Place at absolute index
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,
            },
            # Place after neighbor
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
                "neighbor_placement": "after",
            },
            # Place before neighbor by specification
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
                "neighbor_placement": "before",
            },
            # Place before neighbor by default
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
            },
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(expected.tostring(), actual.tostring())

    def test_transform_entity__parent_found__no_children(self):

        METADATA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
    </platformActionList>
</Layout>
"""

        EXPECTED_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = fromstring(EXPECTED_XML.encode("utf-8"))

        for options in [
            # Place at original index if exists else at the end
            {"action_name": self.action_name, "action_type": self.action_type},
            # Place at absolute index
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,
            },
            # Place after neighbor
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
                "neighbor_placement": "after",
            },
            # Place before neighbor by specification
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
                "neighbor_placement": "before",
            },
            # Place before neighbor by default
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
            },
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(expected.tostring(), actual.tostring())

    def test_transform_entity__parent_found__add_targeted_child_before_neighbor(self):

        METADATA_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.neighbor_action_name}</actionName>
            <actionType>{self.neighbor_action_type}</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        EXPECTED_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.neighbor_action_name}</actionName>
            <actionType>{self.neighbor_action_type}</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>3</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = fromstring(EXPECTED_XML.encode("utf-8"))

        for options in [
            # Place before neighbor by specification
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
                "neighbor_placement": "before",
            },
            # Place before neighbor by default
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
            },
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(expected.tostring(), actual.tostring())

    def test_transform_entity__parent_found__add_targeted_child_after_neighbor(self):

        METADATA_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.neighbor_action_name}</actionName>
            <actionType>{self.neighbor_action_type}</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        EXPECTED_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.neighbor_action_name}</actionName>
            <actionType>{self.neighbor_action_type}</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>3</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = fromstring(EXPECTED_XML.encode("utf-8"))

        for options in [
            # Place after neighbor
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
                "neighbor_placement": "after",
            },
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
                "neighbor_placement": "aFtEr",
            },
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(expected.tostring(), actual.tostring())

    def test_transform_entity__parent_found__add_targeted_child_at_absolute_index_second_last(
        self,
    ):

        METADATA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-1</actionName>
            <actionType>actionName-1</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        EXPECTED_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-1</actionName>
            <actionType>actionName-1</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>3</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = fromstring(EXPECTED_XML.encode("utf-8"))

        for options in [
            # Place at absolute index
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": -2,
            },
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(expected.tostring(), actual.tostring())

    def test_transform_entity__parent_found__add_targeted_child_at_absolute_index_beginning(
        self,
    ):

        METADATA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-1</actionName>
            <actionType>actionName-1</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        EXPECTED_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-1</actionName>
            <actionType>actionName-1</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>3</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = fromstring(EXPECTED_XML.encode("utf-8"))

        for options in [
            # Place at absolute index
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 0,
            },
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(expected.tostring(), actual.tostring())

    def test_transform_entity__parent_found__add_targeted_child_at_end(self):

        METADATA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-1</actionName>
            <actionType>actionName-1</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        EXPECTED_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-1</actionName>
            <actionType>actionName-1</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>3</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = fromstring(EXPECTED_XML.encode("utf-8"))

        for options in [
            # Place at end by default
            {"action_name": self.action_name, "action_type": self.action_type},
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(expected.tostring(), actual.tostring())

    def test_transform_entity__parent_found__add_existing_targeted_child_before_neighbor(
        self,
    ):
        """
        metadata should not be modified if targeted child exists.
        """

        METADATA_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.neighbor_action_name}</actionName>
            <actionType>{self.neighbor_action_type}</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>3</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = None

        for options in [
            # Place before neighbor by specification
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
                "neighbor_placement": "before",
            },
            # Place before neighbor by default
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
            },
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(
                expected,
                actual,
                "None should be returned since metadata was not modified",
            )

            self.assertEqual(
                fromstring(METADATA_XML.encode("utf-8")).tostring(),
                metadata.tostring(),
                "metadata should not be modified",
            )

    def test_transform_entity__parent_found__add_existing_targeted_child_after_neighbor(
        self,
    ):
        """
        metadata should not be modified if targeted child exists.
        """

        METADATA_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.neighbor_action_name}</actionName>
            <actionType>{self.neighbor_action_type}</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>3</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = None

        for options in [
            # Place after neighbor
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
                "neighbor_placement": "after",
            },
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 2,  # overridden by neighbor
                "neighbor_action_type": self.neighbor_action_type,
                "neighbor_action_name": self.neighbor_action_name,
                "neighbor_placement": "aFtEr",
            },
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(
                expected,
                actual,
                "None should be returned since metadata was not modified",
            )

            self.assertEqual(
                fromstring(METADATA_XML.encode("utf-8")).tostring(),
                metadata.tostring(),
                "metadata should not be modified",
            )

    def test_transform_entity__parent_found__add_existing_targeted_child_at_absolute_index_second_last(
        self,
    ):
        """
        metadata should not be modified if targeted child exists.
        """

        METADATA_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-1</actionName>
            <actionType>actionName-1</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>3</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = None

        for options in [
            # Place at absolute index
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": -1,
            },
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(
                expected,
                actual,
                "None should be returned since metadata was not modified",
            )

            self.assertEqual(
                fromstring(METADATA_XML.encode("utf-8")).tostring(),
                metadata.tostring(),
                "metadata should not be modified",
            )

    def test_transform_entity__parent_found__add_existing_targeted_child_at_absolute_index_beginning(
        self,
    ):
        """
        metadata should not be modified if targeted child exists.
        """

        METADATA_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-1</actionName>
            <actionType>actionName-1</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>3</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = None

        for options in [
            # Place at absolute index
            {
                "action_name": self.action_name,
                "action_type": self.action_type,
                "index_placement": 0,
            },
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(
                expected,
                actual,
                "None should be returned since metadata was not modified",
            )

            self.assertEqual(
                fromstring(METADATA_XML.encode("utf-8")).tostring(),
                metadata.tostring(),
                "metadata should not be modified",
            )

    def test_transform_entity__parent_found__add_existing_targeted_child_at_original_index(
        self,
    ):
        """
        metadata should not be modified if targeted child exists.
        """

        METADATA_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Layout xmlns="http://soap.sforce.com/2006/04/metadata">
    <platformActionList>
        <actionListContext>Record</actionListContext>
        <platformActionListItems>
            <actionName>{self.action_name}</actionName>
            <actionType>{self.action_type}</actionType>
            <sortOrder>0</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-0</actionName>
            <actionType>actionName-0</actionType>
            <sortOrder>1</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-1</actionName>
            <actionType>actionName-1</actionType>
            <sortOrder>2</sortOrder>
        </platformActionListItems>
        <platformActionListItems>
            <actionName>actionName-2</actionName>
            <actionType>actionType-2</actionType>
            <sortOrder>3</sortOrder>
        </platformActionListItems>
    </platformActionList>
</Layout>
"""

        expected = None

        for options in [
            # Place at end by default
            {"action_name": self.action_name, "action_type": self.action_type},
        ]:
            metadata = fromstring(METADATA_XML.encode("utf-8"))

            task = create_task(InsertRecordPlatformActionListItem, options)

            actual = task._transform_entity(metadata, self.api_name)

            self.assertEqual(
                expected,
                actual,
                "None should be returned since metadata was not modified",
            )

            self.assertEqual(
                fromstring(METADATA_XML.encode("utf-8")).tostring(),
                metadata.tostring(),
                "metadata should not be modified",
            )
