from typing import Dict

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement
from cumulusci.core.utils import process_bool_arg, process_list_arg


class AddPicklistEntries(MetadataSingleEntityTransformTask):
    entity = "CustomObject"
    task_options = {
        "picklists": {
            "description": "List of picklists to affect, in Object__c.Field__c form.",
            "required": True,
        },
        "entries": {
            "description": "Array of picklist values to insert. "
            "Each value should contain the keys 'fullName', the API name of the entry, "
            "and 'label', the user-facing label. Optionally, specify 'default` on exactly one "
            "entry to make that value the default.",
            "required": True,
        },
        "record_types": {
            "description": "List of Record Type developer names for which the new values "
            "should be available. Any Record Types not present in the target org will be "
            "ignored, and * is a wildcard. Default behavior is to do nothing."
        },
        "sort_values": {"description": "Sort the picklist values alphabetically."},
        "force_last": {
            "description": "Require a specific value to appear last in the list."
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        self.task_config.options["api_names"] = "dummy"
        super()._init_options(kwargs)

        self.picklists = {}
        for pl in self.options["picklists"]:
            obj, field = pl.split(".")
            if None in [obj, field]:
                raise TaskOptionsError(
                    f"Picklist {pl} is not a valid Object.Field reference"
                )
            if not field.endswith("__c"):
                raise TaskOptionsError(
                    "This task only supports custom fields. To modify "
                    "Standard Value Sets, use the add_standard_value_set_entries task."
                )

            self.picklists.setdefault(self._inject_namespace(obj), []).append(
                self._inject_namespace(field)
            )

        if not all(["fullName" in entry for entry in self.options["entries"]]):
            raise TaskOptionsError(
                "The 'fullName' key is required on all picklist values."
            )

        if (
            len(
                list(
                    x
                    for x in self.options["entries"]
                    if process_bool_arg(x.get("default", False))
                )
            )
            > 1
        ):
            raise TaskOptionsError("Only one default picklist value is allowed.")

        self.options["sort_values"] = process_bool_arg(
            self.options.get("sort_values", False)
        )
        self.options["record_types"] = process_list_arg(
            self.options.get("record_types", [])
        )

        self.api_names = set(self.picklists.keys())

    def _deploy(self):
        raise Exception

    def _transform_entity(self, metadata: MetadataElement, api_name: str):
        for pl in self.picklists[api_name]:
            self._modify_picklist(metadata, api_name, pl)

    def _modify_picklist(self, metadata: MetadataElement, api_name: str, picklist: str):
        # Locate the <fields> entry for this picklist.
        field = metadata.find("fields", fullName=picklist)

        if not field:
            raise TaskOptionsError(f"The field {api_name}.{picklist} was not found.")

        vsd = field.valueSet.valueSetDefinition  # TODO: clamp API > 38

        for entry in self.options["entries"]:
            self._add_picklist_field_entry(vsd, api_name, picklist, entry)

            if self.options["record_types"]:
                self._add_record_type_entries(metadata, api_name, picklist, entry)

        if self.options["sort_values"] and not self.options.get("force_last"):
            vsd.sorted.text = "true"
        elif self.options["sort_values"]:
            # Manually sort values so that we can apply force_last
            pass  # TODO

    def _add_picklist_field_entry(
        self, vsd: MetadataElement, api_name: str, picklist: str, entry: Dict
    ):
        fullName = entry["fullName"]
        label = entry.get("label") or fullName
        default = entry.get("default", False)

        if vsd.find("value", fullName=fullName):
            self.logger.warning(
                f"Picklist entry with fullName {fullName} already exists on picklist {picklist}"
            )
        else:
            entry_element = vsd.append("value")
            entry_element.append("fullName", text=fullName)
            entry_element.append("label", text=label)
            entry_element.append(
                "default", text=str(default).lower()
            )  # TODO: enforce one default value

    def _add_record_type_entries(
        self, metadata: MetadataElement, api_name: str, picklist: str, entry: Dict
    ):
        for record_type in self.options["record_types"]:
            rt_element = metadata.find("recordTypes", fullName=record_type)

            # Silently ignore record types that don't exist in the target org.
            if rt_element:
                # Locate, or add, the root picklistValues element for this picklist.
                picklist_element = rt_element.find(
                    "picklistValues", picklist=picklist
                ) or rt_element.append("picklistValues")
                if not picklist_element.find("picklist", text=picklist):
                    picklist_element.append("picklist", text=picklist)

                # If this picklist value entry is not already present, add it.
                if not picklist_element.find("values", fullName=entry["fullName"]):
                    values = picklist_element.append("values")
                    values.append("fullName", text=entry["fullName"])

                # If this picklist value needs to be made default, do so, and remove any existing default.
                if process_bool_arg(entry.get("default", False)):
                    # Find existing default and remove it.

                    for value in picklist_element.values:
                        value.default.text = (
                            "false"
                            if value.fullName.text != entry["fullName"]
                            else "true"
                        )
