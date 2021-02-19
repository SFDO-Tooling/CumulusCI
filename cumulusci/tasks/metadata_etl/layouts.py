from typing import Optional

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
        layout_section = self._inject_namespace(self.options.get("layout_section") or "Information")

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

    def _set_adding_fields(self, metadata, api_name, layout_section_name, adding_fields):
        ## If no fields are passed in, do nothing
        if len(adding_fields) == 0:
            return

        # Find specified layout sections to add fields to
        layout_section_element = metadata.find("layoutSections", label=layout_section_name)
        
        # If layout section doesn't exist, exit gracefully with appropriate message
        if layout_section_element is None:
            raise CumulusCIException("Layout section doesn't exist, task failed")

        layout_columns_element = layout_section_element.find("layoutColumns")

        for f in adding_fields:
            layout_items_element = layout_columns_element.append("layoutItems")
            layout_items_element.append("behavior", "Edit")
            layout_items_element.append("field", f)
