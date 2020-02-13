from lxml import etree

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import (
    MetadataSingleEntityTransformTask,
    get_new_tag_index,
    MD,
)


class AddValueSetEntries(MetadataSingleEntityTransformTask):
    entity = "StandardValueSet"
    task_options = {
        "entries": {
            "description": "Array of standardValues to insert. "
            "Each standardValue should contain the keys 'fullName', the API name of the entry, "
            "and 'label', the user-facing label. OpportunityStage entries require the additional "
            "keys 'closed', 'won', 'forecastCategory', and 'probability'; CaseStatus entries "
            "require 'closed'.",
            "required": False,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _transform_entity(self, metadata, api_name):
        for entry in self.options.get("entries", []):
            if "fullName" not in entry or "label" not in entry:
                raise TaskOptionsError(
                    "Standard value set entries must contain the 'fullName' and 'label' keys."
                )

            # Check for extra metadata on CaseStatus and OpportunityStage
            if api_name == "OpportunityStage":
                if not all(
                    [
                        "closed" in entry,
                        "forecastCategory" in entry,
                        "probability" in entry,
                        "won" in entry,
                    ]
                ):
                    raise TaskOptionsError(
                        "OpportunityStage standard value set entries require the keys "
                        "'closed', 'forecastCategory', 'probability', and 'won'"
                    )
            if api_name == "CaseStatus":
                if "closed" not in entry:
                    raise TaskOptionsError(
                        "CaseStatus standard value set entries require the key 'closed'"
                    )

            new_entry_index = get_new_tag_index(metadata, "standardValue")

            existing_entry = metadata.findall(
                f".//{MD}standardValue[{MD}fullName='{entry['fullName']}']"
            )
            if not existing_entry:
                # Entry doesn't exist. Insert it.
                elem = etree.Element(f"{MD}standardValue")
                metadata.getroot().insert(new_entry_index, elem)

                elem_fullName = etree.SubElement(elem, f"{MD}fullName")
                elem_fullName.text = entry["fullName"]

                elem_label = etree.SubElement(elem, f"{MD}label")
                elem_label.text = entry["label"]

                elem_default = etree.SubElement(elem, f"{MD}default")
                elem_default.text = "false"

                if api_name in ["OpportunityStage", "CaseStatus"]:
                    elem_closed = etree.SubElement(elem, f"{MD}closed")
                    elem_closed.text = str(entry["closed"]).lower()

                if api_name == "OpportunityStage":
                    elem_won = etree.SubElement(elem, f"{MD}won")
                    elem_won.text = str(entry["won"]).lower()

                    elem_probability = etree.SubElement(elem, f"{MD}probability")
                    elem_probability.text = str(entry["probability"])

                    elem_forecast_category = etree.SubElement(
                        elem, f"{MD}forecastCategory"
                    )
                    elem_forecast_category.text = entry["forecastCategory"]

        return metadata
