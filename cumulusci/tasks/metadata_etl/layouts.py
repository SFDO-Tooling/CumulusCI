from typing import List, Optional

from pydantic.v1 import BaseModel, root_validator
from typing_extensions import Literal

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_bool_arg, process_list_arg
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


class AddFieldsPosition(BaseModel):
    field: Optional[str]
    column: Optional[Literal["first", "last"]]
    relative: Literal["before", "after", "top", "bottom"]
    section: Optional[int]

    @root_validator
    def columns_not_compatible_with_fields(cls, values):
        field, column, section = (
            values.get("field"),
            values.get("column"),
            values.get("section"),
        )
        if (column is not None or section is not None) and field is not None:
            raise ValueError(
                "Section/Column positioning is not compatible when setting a field based position"
            )
        return values

    @root_validator
    def field_uses_before_after(cls, values):
        field, relative = values.get("field"), values.get("relative")
        if (relative == "top" or relative == "bottom") and field is not None:
            raise ValueError(
                'Please use "before" or "after" when setting a field based position.'
            )
        return values

    @root_validator
    def column_uses_before_after(cls, values):
        column, relative = values.get("column"), values.get("relative")
        if (relative == "before" or relative == "after") and column is not None:
            raise ValueError(
                'Please use "top" or "bottom" when setting a column based position.'
            )
        return values


class AddFieldOptions(BaseModel):
    api_name: str
    position: Optional[List[AddFieldsPosition]]
    required: bool = False
    read_only: bool = False


class AddPagesOptions(BaseModel):
    api_name: str
    height: Optional[int]
    show_label: bool = False
    show_scrollbars: bool = False
    width: Optional[str]
    position: Optional[List[AddFieldsPosition]]


class AddFieldsToLayoutOptions(BaseModel):
    fields: Optional[List[AddFieldOptions]]
    pages: Optional[List[AddPagesOptions]]


class AddFieldsToPageLayout(MetadataSingleEntityTransformTask):
    task_docs = """
        Inserts the listed fields or Visualforce pages into page layouts
        specified by API name.

        If the targeted item already exists, the layout metadata is not modified.

        You may supply a single position option, or multiple options for both pages and
        fields. The first option to to be matched will be used.

        Task option details:

        - fields:

            - api_name: [field API name]
            - required: Boolean (default False)
            - read_only: Boolean (default False, not compatible with required)
            - position: (Optional: A list of single or multiple position options.)

                - relative: [before | after | top | bottom]
                - field: [api_name] (Use with relative: before, after)
                - section: [index] (Use with relative: top, bottom)
                - column: [first | last] (Use with relative: top, bottom)

        - pages:

            - api_name: [Visualforce Page API name]
            - height: int (Optional. Default: 200)
            - show_label: Boolean (Optional. Default: False)
            - show_scrollbars: Boolean (Optional. Default: False)
            - width: 0-100% (Optional. Default: 100%)
            - position: (Optional: A list of single or multiple position options.)

                - relative: [before | after | top | bottom]
                - field: [api_name] (Use with relative: before, after)
                - section: [index] (Use with relative: top, bottom)
                - column: [first | last] (Use with relative: top, bottom)

        Example Usage
        -----------------------

        .. code-block::  yaml

            task: add_page_layout_fields
            options:
                api_names: "Contact-Contact Layout"
                fields:
                  - api_name: Giving_Level__c
                    position:
                      - relative: bottom
                        section: 0
                        column: first
                  - api_name: Previous_Giving_Level__c
                    position:
                      - relative: bottom
                        section: 0
                        column: last
            ui_options:
                name: Add custom giving fields to Contact Layout

        """
    entity = "Layout"
    task_options = {
        "fields": {
            "description": "List of fields. See task info for structure.",
            "required": False,
        },
        "pages": {
            "description": "List of Visualforce Pages. See task info for structure.",
            "required": False,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        fields_options = self.options.get("fields")
        pages_options = self.options.get("pages")

        self._validated_options = AddFieldsToLayoutOptions(
            fields=fields_options,
            pages=pages_options,
        )

        self._adding_fields = fields_options
        self._adding_pages = pages_options
        # Split because a page could share an api name with a field in the same namespace
        self._existing_field_names = []
        self._existing_page_names = []

    def _transform_entity(
        self, metadata: MetadataElement, api_name: str
    ) -> Optional[MetadataElement]:

        self._metadata = metadata

        self._collect_existing_items()

        self._add_fields(api_name)
        self._add_pages(api_name)

        return self._metadata

    ## Collect fields already in the layout
    def _collect_existing_items(self):
        ## Need to traverse all layoutSections->layoutColumns->layoutItems->fields to find if item/field already exists
        layout_sections = self._metadata.findall("layoutSections")
        for section in layout_sections:
            layout_columns = section.findall("layoutColumns")
            for col in layout_columns:
                layout_items = col.findall("layoutItems")
                for item in layout_items:
                    if item.find("page"):
                        self._existing_page_names.append(item.page.text)
                    elif item.find("field"):
                        self._existing_field_names.append(item.field.text)

    def _add_fields(self, api_name):
        # Do nothing if there are no fields
        if not self._adding_fields:
            return

        field_props = {
            self._inject_namespace(field["api_name"]): field
            for field in self._adding_fields
        }

        layout_item_dict = self._add_items(
            self._adding_fields, self._existing_field_names, api_name
        )

        for field_item_key in layout_item_dict.keys():
            field = field_props.get(field_item_key)
            field_layout_item = layout_item_dict.get(field_item_key)
            adding_field_name = self._inject_namespace(field.get("api_name"))

            self.logger.info(f"Adding {adding_field_name} to {api_name}")

            behavior = "Edit"
            required = process_bool_arg(field.get("required") or False)
            read_only = process_bool_arg(field.get("read_only") or False)
            if required and not read_only:
                behavior = "Required"
            elif read_only and not required:
                behavior = "Readonly"
            elif required and read_only:
                raise TaskOptionsError(
                    f"`required` and `read_only` cannot both be True for {adding_field_name}"
                )
            field_layout_item.append("behavior", behavior)
            field_layout_item.append("field", adding_field_name)

    def _add_pages(self, api_name):
        # Do nothing if there are no fields
        if not self._adding_pages:
            return

        page_props = {
            self._inject_namespace(page["api_name"]): page
            for page in self._adding_pages
        }

        layout_item_dict = self._add_items(
            self._adding_pages, self._existing_page_names, api_name
        )

        for page_item_key in layout_item_dict.keys():
            page = page_props.get(page_item_key)
            page_layout_item = layout_item_dict.get(page_item_key)
            adding_page_name = self._inject_namespace(page.get("api_name"))

            self.logger.info(f"Adding {adding_page_name} to {api_name}")

            page_layout_item.append("page", adding_page_name)
            page_layout_item.append("height", str(page.get("height", 200)))
            page_layout_item.append(
                "showLabel",
                str(process_bool_arg(page.get("show_label") or False)).lower(),
            )
            page_layout_item.append(
                "showScrollbars",
                str(process_bool_arg(page.get("show_scrollbars") or False)).lower(),
            )
            page_layout_item.append("width", page.get("width", "100%"))

    def _add_items(self, item_list, existing_name_list, api_name):
        """Iterate over a list of new layout items that will return a dict{api_name:MetadataElement}"""

        item_dict = {}

        for item in item_list:
            item_name = self._inject_namespace(item.get("api_name"))
            if item_name in existing_name_list:
                self.logger.warning(
                    f"Skipped {item_name} because {item_name} is already present in {api_name}"
                )
                continue

            item_dict[item_name] = self._position_item(item)

        return item_dict

    def _position_item(self, new_item):
        """Returns new MetadataElement being added to the layout based on the positioning properties"""
        new_item_name = new_item.get("api_name")
        # Default to top of first section (index zero) of last column
        default = {
            "relative": "top",
            "section": 0,
            "column": "last",
        }

        # Position is optional
        position = new_item.get("position")

        if position is None:
            self.logger.warning(
                f"Position details are missing for: {new_item_name}. Default position is being applied."
            )
            position = [default]
        else:
            # append the default position to the list as a fallback
            position.append(default)

        for pos in position:
            new_layout_item = self._process_position(pos, default)
            if new_layout_item is not None:
                return new_layout_item

    def _process_position(self, position, default_position):
        """Attempt to apply a position specifier and return a MetadataElement representing a layout item, or None if the position specifier cannot be applied."""
        relative_position = position.get("relative", default_position.get("relative"))

        # Mutually exclusive, therefore the higher priority is field if specified
        relative_field_name = None
        if "field" in position:
            relative_field_name = (
                self._inject_namespace(position.get("field"))
                if position.get("field") is not None
                else None
            )
            relative_section_index = None
            if relative_position in ("top", "bottom"):
                # Missing a relative position to the field, therefore default to after
                relative_position = "after"
        elif "section" in position:
            relative_section_index = position.get("section")
        else:
            relative_section_index = default_position.get("section")
            relative_position = default_position.get("position")

        new_layout_item = None

        # Field relative
        if relative_field_name is not None and relative_position in (
            "before",
            "after",
        ):
            new_layout_item = self._new_layout_item(
                relative_field_name, relative_position
            )

        # Section relative
        if relative_section_index is not None and relative_position in (
            "top",
            "bottom",
        ):
            new_layout_item = self._new_section_item(
                relative_section_index,
                relative_position,
                position.get("column", default_position.get("column")),
            )

        return new_layout_item

    def _new_layout_item(self, field_text, position):
        for section in self._metadata.findall("layoutSections"):
            for col in section.findall("layoutColumns"):
                for item in col.findall("layoutItems"):
                    for field in item.findall("field"):
                        if field.text == field_text:
                            return getattr(col, "insert_" + position)(
                                item, "layoutItems"
                            )

    def _new_section_item(self, index, position, column_index):
        # Get section at index
        sections = list(self._metadata.findall("layoutSections"))

        if index > (len(sections) - 1):
            self.logger.warning(
                f"Unable to find section at index: {str(index)}. Default position is being selected."
            )
            return None

        section = sections[index]
        columns = list(section.findall("layoutColumns"))
        column = columns[-1 if column_index == "last" else 0]
        items = list(column.findall("layoutItems"))
        # Sections can be empty
        if len(items) == 0 or position == "bottom":
            return column.append("layoutItems")
        else:
            item_relative_position = "before" if position == "top" else "after"
            return getattr(column, "insert_" + item_relative_position)(
                items[0], "layoutItems"
            )


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
