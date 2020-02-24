from lxml import etree

from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.metadata_etl import (
    MetadataSingleEntityTransformTask,
    get_new_tag_index,
    MD,
)


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

    def _transform_entity(self, metadata, api_name):
        new_related_list_index = get_new_tag_index(metadata, "relatedLists")
        related_list = self._inject_namespace(self.options["related_list"])
        existing_related_lists = metadata.findall(
            f".//{MD}relatedLists[{MD}relatedList='{related_list}']"
        )

        if existing_related_lists:
            return None

        self._create_new_related_list(
            metadata, api_name, related_list, new_related_list_index
        )

        return metadata

    def _create_new_related_list(self, metadata, api_name, related_list, index):
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

        elem = etree.Element(f"{MD}relatedLists")
        metadata.getroot().insert(index, elem)

        for f in fields:
            elem_field = etree.SubElement(elem, f"{MD}fields")
            elem_field.text = f

        for button in exclude_buttons:
            elem_button = etree.SubElement(elem, f"{MD}excludeButtons")
            elem_button.text = button

        for button in custom_buttons:
            elem_button = etree.SubElement(elem, f"{MD}customButtons")
            elem_button.text = button

        elem_related_list = etree.SubElement(elem, f"{MD}relatedList")
        elem_related_list.text = related_list
