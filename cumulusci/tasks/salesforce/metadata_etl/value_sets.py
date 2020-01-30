import xml.etree.ElementTree as XML_ET

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.metadata_etl import (
    MetadataSingleEntityTransformTask,
    get_new_tag_index,
)


class AddValueSetEntries(MetadataSingleEntityTransformTask):
    entity = "StandardValueSet"
    task_options = {
        "entries": {
            "description": "Array of standardValues to insert. Each standardValue should contain the keys 'fullName', the API name of the entry; 'label', the user-facing label.",
            "required": "False",
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _transform_entity(self, metadata, api_name):
        for entry in self.options.get("entries", []):
            if "fullName" not in entry or "label" not in entry:
                raise TaskOptionsError(
                    "Standard value set entries must contain the 'fullName' and 'label' keys."
                )

            new_entry_index = get_new_tag_index(
                metadata, "standardValue", self.namespaces
            )

            existing_entry = metadata.findall(
                f".//sf:standardValue[sf:fullName='{entry['fullName']}']",
                self.namespaces,
            )
            if not existing_entry:
                # Entry doesn't exist. Insert it.
                elem = XML_ET.Element("{%s}standardValue" % (self.namespaces.get("sf")))
                metadata.getroot().insert(new_entry_index, elem)

                elem_fullName = XML_ET.SubElement(
                    elem, "{%s}fullName" % (self.namespaces.get("sf"))
                )
                elem_fullName.text = entry["fullName"]

                elem_label = XML_ET.SubElement(
                    elem, "{%s}label" % (self.namespaces.get("sf"))
                )
                elem_label.text = entry["label"]

                elem_default = XML_ET.SubElement(
                    elem, "{%s}default" % (self.namespaces.get("sf"))
                )
                elem_default.text = "false"

        return metadata
