import xml.etree.ElementTree as XML_ET
from cumulusci.core.utils import process_list_arg

from cumulusci.tasks.salesforce.metadata_etl import (
    MetadataSingleEntityTransformTask,
    get_new_tag_index,
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
            "required": "False",
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _transform_entity(self, metadata, api_name):
        new_related_list_index = get_new_tag_index(
            metadata, "relatedLists", self.namespaces
        )
        related_list = self._namespace_injector(self.options["related_list"])
        existing_related_lists = metadata.findall(
            f".//sf:relatedLists[sf:relatedList='{related_list}']", self.namespaces
        )

        if not existing_related_lists:
            self._create_new_related_list(
                metadata, api_name, related_list, new_related_list_index
            )

        return metadata

    def _create_new_related_list(self, metadata, api_name, related_list, index):
        self.logger.info(f"Adding Related List {related_list} to {api_name}")

        fields = [
            self._namespace_injector(f)
            for f in process_list_arg(self.options.get("fields", []))
        ]

        elem = XML_ET.Element("{%s}relatedLists" % (self.namespaces.get("sf")))
        metadata.getroot().insert(index, elem)

        for f in fields:
            elem_field = XML_ET.SubElement(
                elem, "{%s}fields" % (self.namespaces.get("sf"))
            )
            elem_field.text = f

        elem_related_list = XML_ET.SubElement(
            elem, "{%s}relatedList" % (self.namespaces.get("sf"))
        )
        elem_related_list.text = related_list
