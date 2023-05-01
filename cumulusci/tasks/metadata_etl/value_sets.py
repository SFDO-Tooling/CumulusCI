from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement

CASE_STATUS_ERR = "CaseStatus standard value set entries require the key 'closed'"
LEAD_STATUS_ERR = "LeadStatus standard value set entries require the key 'converted'"
FULL_NAME_AND_LABEL_ERR = (
    "Standard value set entries must contain the 'fullName' and 'label' keys."
)
OPP_STAGE_ERR = (
    "OpportunityStage standard value set entries require the keys "
    "'closed', 'forecastCategory', 'probability', and 'won'"
)


class AddValueSetEntries(MetadataSingleEntityTransformTask):
    task_docs = """

        Example Usage
        -----------------------

        .. code-block::  yaml

            task: add_standard_value_set_entries
            options:
                api_names: CaseOrigin
                entries:
                    - fullName: New Account
                      label: New Account
                    - fullName: Questionable Contact
                      label: Questionable Contact
                ui_options:
                    name: Add values to Case Origin picklist

        """

    entity = "StandardValueSet"
    task_options = {
        **MetadataSingleEntityTransformTask.task_options,
        "entries": {
            "description": "Array of standardValues to insert. "
            "Each standardValue should contain the keys 'fullName', the API name of the entry, "
            "and 'label', the user-facing label. OpportunityStage entries require the additional "
            "keys 'closed', 'won', 'forecastCategory', and 'probability'; CaseStatus entries "
            "require 'closed'; LeadStatus entries require 'converted'.",
            "required": True,
        },
        "api_names": {
            "description": "List of API names of StandardValueSets to affect, "
            "such as 'OpportunityStage', 'AccountType', 'CaseStatus', 'LeadStatus'",
            "required": True,
        },
    }

    def _transform_entity(self, metadata: MetadataElement, api_name: str):
        for entry in self.options.get("entries", []):
            if "fullName" not in entry or "label" not in entry:
                raise TaskOptionsError(FULL_NAME_AND_LABEL_ERR)

            # Check for extra metadata on CaseStatus, OpportunityStage and LeadStatus
            if api_name == "OpportunityStage":
                if not all(
                    [
                        "closed" in entry,
                        "forecastCategory" in entry,
                        "probability" in entry,
                        "won" in entry,
                    ]
                ):
                    raise TaskOptionsError(OPP_STAGE_ERR)
            if api_name == "CaseStatus":
                if "closed" not in entry:
                    raise TaskOptionsError(CASE_STATUS_ERR)
            if api_name == "LeadStatus":
                if "converted" not in entry:
                    raise TaskOptionsError(LEAD_STATUS_ERR)

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

                if api_name == "LeadStatus":
                    elem.append("converted", str(entry["converted"]).lower())

        return metadata
