from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement


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

    def _transform_entity(self, metadata: MetadataElement, api_name: str):
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

            existing_entry = metadata.findall(
                "standardValue", fullName=entry["fullName"]
            )

            if not existing_entry:
                # Entry doesn't exist. Insert it.
                elem = metadata.append(tag="standardValue")
                elem.append("fullName", text=entry["fullName"])

                elem.append("label", text=entry["label"])

                elem.append("default", text="false")

                if api_name in ["OpportunityStage", "CaseStatus"]:
                    elem.append("closed", str(entry["closed"]).lower())

                if api_name == "OpportunityStage":
                    elem.append("won", str(entry["won"]).lower())
                    elem.append("probability", str(entry["probability"]))
                    elem.append("forecastCategory", entry["forecastCategory"])

        return metadata
