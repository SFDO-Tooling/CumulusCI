from typing import Optional

from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.metadata_etl import (
    MetadataSingleEntityTransformTask,
    InsertChildInMetadataSingleEntityTransformTask,
)
from cumulusci.utils.xml.metadata_tree import MetadataElement


class AddRelatedLists(MetadataSingleEntityTransformTask):
    entity = "Layout"
    task_options = {
        "related_list": {
            "description": "Name of the Related List to include",
            "required": True,
        },
        "fields": {
            "description": "Array of field API names to include in the related list",
            "required": False,
        },
        "exclude_buttons": {
            "description": "Array of button names to suppress from the related list"
        },
        "custom_buttons": {
            "description": "Array of button names to add to the related list"
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _transform_entity(
        self, metadata: MetadataElement, api_name: str
    ) -> Optional[MetadataElement]:
        related_list = self._inject_namespace(self.options["related_list"])
        existing_related_lists = metadata.findall(
            "relatedLists", relatedList=related_list
        )

        if existing_related_lists:
            return None

        self._create_new_related_list(metadata, api_name, related_list)

        return metadata

    def _create_new_related_list(self, metadata, api_name, related_list):
        self.logger.info(f"Adding Related List {related_list} to {api_name}")

        fields = [
            self._inject_namespace(f)
            for f in process_list_arg(self.options.get("fields", []))
        ]
        exclude_buttons = [
            self._inject_namespace(f)
            for f in process_list_arg(self.options.get("exclude_buttons", []))
        ]
        custom_buttons = [
            self._inject_namespace(f)
            for f in process_list_arg(self.options.get("custom_buttons", []))
        ]

        elem = metadata.append("relatedLists")

        for f in fields:
            elem.append("fields", text=f)

        for button in exclude_buttons:
            elem.append("excludeButtons", button)

        for button in custom_buttons:
            elem.append("customButtons", button)

        elem.append("relatedList", text=related_list)


class InsertRecordPlatformActionListItem(
    InsertChildInMetadataSingleEntityTransformTask
):
    """
    "Salesforce Mobile and Lightning Experience Actions", the buttons/actions
    available in layouts in Lightning Experience, are platformActionListItems
    in the layout's platformActionList with actionListContext "Record".

    This task is an ETL style task that inserts the targeted lightning
    button/action in the specified layout.  If the targeted lightning
    button/action already exists, the layout metadata is not modified.
    """

    entity = "Layout"
    task_options = {
        "action_type": {
            "description": "platformActionListItems.actionType.  See documentation: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_layouts.htm#PlatformActionListItem",  # noqa: E501
            "required": True,
        },
        "action_name": {
            "description": "platformActionListItems.actionName.  See documentation: https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_layouts.htm#PlatformActionListItem",  # noqa: E501
            "required": True,
        },
        "neighbor_action_type": {
            "description": 'The platformActionListItems.actionType of the neighbor platformActionListItems to create or move the specified platformActionListItems.  The "neighbor" options are ignored if the neighbor cannot be found or the neighbor_placement is invalid.',  # noqa: E501
            "required": False,
        },
        "neighbor_action_name": {
            "description": 'The platformActionListItems.actionName of the neighbor platformActionListItems to create or move the specified platformActionListItems.  The "neighbor" options are ignored if the neighbor cannot be found or the neighbor_placement is invalid.',  # noqa: E501
            "required": False,
        },
        **InsertChildInMetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self._action_type = self.options.get("action_type", "")
        self._action_name = self._inject_namespace(self.options.get("action_name", ""))
        self._neighbor_action_type = self.options.get("neighbor_action_type")

        self._neighbor_action_name = None
        if self.options.get("neighbor_action_name") is not None:
            self._neighbor_action_name = self._inject_namespace(
                self.options.get("neighbor_action_name")
            )

    def _is_targeted_child(self, child: MetadataElement) -> bool:
        """
        child is the "new child" if:
        - child.actionType equals action_type option
        - child.actionName equals action_name option
        """
        return (
            child.actionType.text == self._action_type
            and child.actionName.text == self._action_name
        )

    def _is_targeted_child_neighbor(self, child: MetadataElement) -> bool:
        """
        child is the "neighbor" if:
        - both neighbor_action_type and neighbot_action_names are set
        - child.actionType equals neighbor_action_type option
        - child.actionName equals neighbot_action_name option
        """
        return (
            self._neighbor_action_type is not None
            and self._neighbor_action_name is not None
            and child.actionType.text == self._neighbor_action_type
            and child.actionName.text == self._neighbor_action_name
        )

    def _populate_targeted_child(self, targeted_child: MetadataElement) -> None:
        targeted_child.append("actionName", self._action_name)
        targeted_child.append("actionType", self._action_type)

    def _update_platform_action_list_items_sort_order(
        self, platform_action_list: MetadataElement
    ):
        """
        Set each child's sortOrder as the index in children.  If the sortOrder
        is not set to match the list index, the platformActionListItems
        will not be deployed in the order expected.
        """
        for index, child in enumerate(
            platform_action_list.findall("platformActionListItems")
        ):
            sortOrder = child.find("sortOrder")
            if not sortOrder:
                sortOrder = child.append("sortOrder")
            sortOrder.text = str(index)

    def _transform_entity(
        self, metadata: MetadataElement, api_name: str
    ) -> Optional[MetadataElement]:
        """
        Inserts targeted child in metadata's "Record" platformActionList's
        platformActionListItems.

        If metadata's "Record" platformActionlist is modified, updates
        platformActionListItems' sortOrder then returns metadata for
        deployment.

        Else, returns None if "Record" platformActionList is not modified.
        """
        record_platform_action_list = metadata.find(
            "platformActionList", actionListContext="Record"
        )

        if not record_platform_action_list:
            # If not record_platform_action_list, then the layout will always
            # be modified since this task will insert the targeted child in
            # the empty record_platform_action_list.
            record_platform_action_list = metadata.append("platformActionList")
            record_platform_action_list.append("actionListContext", text="Record")

        self.logger.info(f'Appending platformActionListItems for layout "{api_name}"')
        self.logger.info("")

        is_parent_modified = self._insert_targeted_child_in_parent(
            record_platform_action_list, "platformActionListItems"
        )

        if is_parent_modified:
            self._update_platform_action_list_items_sort_order(
                record_platform_action_list
            )
            return metadata
