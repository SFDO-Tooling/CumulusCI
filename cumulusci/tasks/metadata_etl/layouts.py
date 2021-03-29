from typing import Optional
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
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


class AddRecordPlatformActionListItem(MetadataSingleEntityTransformTask):
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
        # TODO refactor - use something like "place_first" - and make boolean, default is false.
        # TODO - use placement to indicate if targeting before or after a tag (not sure how best that option would look)
        "placement": {
            "description": 'Valid options: "first" or "last". Denotes where to place the action - at the beginning or end of current ActionListItems, defaults to end',  # noqa: E501
            "required": False,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        # TODO - refactor, not needed if we use a bool and assume first or last placement.
        self.valid_placements = ["first", "last"]
        self._action_type = self.options.get("action_type", "")
        self._action_name = self._inject_namespace(self.options.get("action_name", ""))

        if not self.options.get("placement"):
            self._action_placement = "last"
        else:
            self._action_placement = self.options.get("placement")

        if self._action_placement not in self.valid_placements:
            raise TaskOptionsError(
                "Valid options for `placement` are 'first' or 'last'"
            )

    def _transform_entity(
        self, metadata: MetadataElement, api_name: str
    ) -> Optional[MetadataElement]:

        existing_action_list = metadata.find(
            "platformActionList", actionListContext="Record"
        )

        if not existing_action_list:
            existing_action_list = metadata.append("platformActionList")
            existing_action_list.append("actionListContext", "Record")

        # TODO method?
        # check for existing platform Action List Item of same name and exit
        if existing_action_list.find(
            "platformActionListItems", actionName=self._action_name
        ):
            return None
        # append action item! before or after? not sure. How do we use insert before and after?
        #   get a count of all items?
        self._create_new_action_list_item(existing_action_list)
        self._update_platform_action_list_items_sort_order(existing_action_list)

        return metadata

    def _create_new_action_list_item(self, existing_action_list):
        """
        TODO - fill this out
        """
        # TODO - refactor opportunities?
        if self._action_placement == "first" and existing_action_list.find(
            "platformActionListItems"
        ):
            existing_action_list.insert_after(
                existing_action_list.find("actionListContext"),
                "platformActionListItems",
            )
            action_list_item = existing_action_list.find("platformActionListItems")
        else:
            action_list_item = existing_action_list.append("platformActionListItems")

        action_list_item.append("actionName", self._action_name)
        action_list_item.append("actionType", self._action_type)
        # SortOrder needs to be an integer, but we tag it with the placement desired so we can find it
        action_list_item.append("sortOrder", self._action_placement)

    def _update_platform_action_list_items_sort_order(self, existing_action_list):
        """
        TODO - fill this out
        """
        # update the sortOrder of the ActionPlanListItem
        for index, child in enumerate(
            existing_action_list.findall("platformActionListItems")
        ):
            sortOrder = child.find("sortOrder")
            sortOrder.text = str(index)
