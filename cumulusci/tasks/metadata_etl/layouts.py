from typing import Optional
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.utils import process_list_arg, process_bool_arg
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


class AddFields(MetadataSingleEntityTransformTask):
    entity = "Layout"
    task_options = {
        "layout_section": {
            "description": "Which layout section the fields should be added to, default is Information",
            "required": False,
        },
        "fields": {
            "description": "Array of field API names to append to specified layout section",
            "required": True,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _transform_entity(
        self, metadata: MetadataElement, api_name: str
    ) -> Optional[MetadataElement]:

        # Set layout section and default to "Information" section if not passed in
        layout_section = self._inject_namespace(
            self.options.get("layout_section") or "Information"
        )

        # Set fields to be added to layout section
        adding_fields = [
            self._inject_namespace(field)
            for field in process_list_arg(self.options.get("fields", []))
        ]

        self._remove_existing_fields(metadata, api_name, adding_fields)

        self._set_adding_fields(metadata, api_name, layout_section, adding_fields)

        return metadata

    ## If fields passed in that already exist in the Page Layout, remove from current sections
    def _remove_existing_fields(self, metadata, api_name, adding_fields):

        ## Need to traverse all layoutSections->layoutColumns->layoutItems->fields to find if item/field already exists
        layout_sections = metadata.findall("layoutSections")
        for section in layout_sections:
            layout_columns = section.findall("layoutColumns")
            for col in layout_columns:
                layout_items = col.findall("layoutItems")
                for item in layout_items:
                    if item.field.text in adding_fields:
                        # remove that item from existing layout to be re-added
                        col.remove(item)

    def _set_adding_fields(
        self, metadata, api_name, layout_section_name, adding_fields
    ):
        ## If no fields are passed in, do nothing
        if len(adding_fields) == 0:
            return

        # Find specified layout sections to add fields to
        layout_section_element = metadata.find(
            "layoutSections", label=layout_section_name
        )

        # If layout section doesn't exist, exit gracefully with appropriate message
        if layout_section_element is None:
            raise CumulusCIException("Layout section doesn't exist, task failed")

        layout_columns_element = layout_section_element.find("layoutColumns")

        for f in adding_fields:
            layout_items_element = layout_columns_element.append("layoutItems")
            layout_items_element.append("behavior", "Edit")
            layout_items_element.append("field", f)


class AddRecordPlatformActionListItem(MetadataSingleEntityTransformTask):
    task_docs = """
        Inserts the targeted lightning button/action into specified
        layout's PlatformActionList with a 'Record' actionListContext.
        - If the targeted lightning button/action already exists,
            the layout metadata is not modified.
        - If there is no 'Record' context PlatformActionList,
            we will generate one and add the specified action

        Task definition example:

            dev_inject_apply_quick_action_into_account_layout:
            group: "Demo config and storytelling"
            description: Adds an Apply Quick Action button to the beggining of the button list on the Experiences Account Layout.
            class_path: tasks.layouts.InsertRecordPlatformActionListItem
            options:
                api_names: "Account-%%%NAMESPACE%%%Experiences Account Layout"
                action_name: "Account.Apply"
                action_type: QuickAction
                place_first: True

        Reference Documentation:
        https://developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_layouts.htm#PlatformActionList
        """

    entity = "Layout"
    task_options = {
        "action_type": {
            "description": "platformActionListItems.actionType like 'QuickAction' or 'CustomButton'",
            "required": True,
        },
        "action_name": {
            "description": "platformActionListItems.actionName. The API name for the action to be added.",
            "required": True,
        },
        "place_first": {
            "description": "When 'True' the specified Record platformActionListItem will be inserted before any existing on the layout. Default is 'False'",
            "required": False,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self._action_type = self.options.get("action_type", "")
        self._action_name = self._inject_namespace(self.options.get("action_name", ""))
        # Default to False if `place_first` option was not set
        self._place_first = process_bool_arg(self.options.get("place_first") or False)

    def _transform_entity(
        self, metadata: MetadataElement, api_name: str
    ) -> Optional[MetadataElement]:
        # get or create an existing action list
        self._existing_action_list = self._get_existing_action_list(metadata)

        # check for existing Platform Action List Item of same name
        #   (i.e. The desired QuickAction is in this layout already)
        if self._existing_action_list.find(
            "platformActionListItems", actionName=self._action_name
        ):
            self.logger.info(
                f"Action named {self._action_name} already exists in {api_name}, task exiting without modifying layout."
            )
            return None

        # create an action list item
        self._create_new_action_list_item(self._existing_action_list)
        self._update_platform_action_list_items_sort_order(self._existing_action_list)
        return metadata

    def _get_existing_action_list(self, metadata: MetadataElement):
        existing_action_list = metadata.find(
            "platformActionList", actionListContext="Record"
        )
        if not existing_action_list:
            existing_action_list = metadata.append("platformActionList")
            existing_action_list.append("actionListContext", "Record")

        return existing_action_list

    def _create_new_action_list_item(self, existing_action_list):
        if self._place_first and existing_action_list.find("platformActionListItems"):
            existing_action_list.insert_after(
                existing_action_list.find("actionListContext"),
                "platformActionListItems",
            )
            action_list_item = existing_action_list.find("platformActionListItems")
        else:
            action_list_item = existing_action_list.append("platformActionListItems")

        action_list_item.append("actionName", self._action_name)
        action_list_item.append("actionType", self._action_type)
        action_list_item.append("sortOrder", "place_first:" + str(self._place_first))

    def _update_platform_action_list_items_sort_order(self, existing_action_list):
        """
        Updates the sortOrder element of the platformActionListItems
            Takes a platformActionList (MetadatataElement) and sets the sortOrder according
            to platformActionListItem placement relative to siblings
        """
        for index, child in enumerate(
            existing_action_list.findall("platformActionListItems")
        ):
            sortOrder = child.find("sortOrder")
            sortOrder.text = str(index)
