from typing import Optional

from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement


class AddLayoutSectionField(MetadataSingleEntityTransformTask):
    entity = "Layout"
    task_options = {
        "label": {
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
        label = self._inject_namespace(self.options["label"])
        existing_search_layouts = metadata.findall("layoutSections")

        if not existing_search_layouts:
            raise Exception("Are you sure this search layout exists?")
        breakpoint()
        self._create_new_layout_section_field(
            existing_search_layouts, api_name, label, "field"
        )
        breakpoint()
        return metadata

    def _create_new_layout_section_field(self, metadata, api_name, label, field):
        self.logger.info(
            f"Adding Field {field} on the layoutSection {label} to {api_name}"
        )
        # fields = [
        #     self._inject_namespace(f)
        #     for f in process_list_arg(self.options.get("fields", []))
        # ]
        for layoutSection in metadata:
            if label == layoutSection.label.text:
                elem = layoutSection.layoutColumns
                elem.append("layoutItems")
                elem.append("behavior", text="Required")
                elem.append("field", text=field)
                elem.append("layoutItems")

                # for f in fields:
                #     elem.append("fields", text=f)

        # elem.append("layoutSections", text=label)


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
