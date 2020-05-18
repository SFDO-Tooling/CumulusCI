from collections import defaultdict
from typing import Dict
from urllib.parse import unquote

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
            "and 'label', the user-facing label. Optionally, specify `default: True` on exactly one "
            "entry to make that value the default. Any existing values will not be affected other than "
            "setting the default (labels of existing entries are not changed).\n"
            "To order values, include the 'add_before' key. This will insert the new value "
            "before the existing value with the given API name, or at the end of the list if not present.",
            "required": True,
        },
        "record_types": {
            "description": "List of Record Type developer names for which the new values "
            "should be available. If any of the entries have `default: True`, they are also made "
            "default for these Record Types. Any Record Types not present in the target org will be "
            "ignored, and * is a wildcard. Default behavior is to do nothing."
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        self.task_config.options["api_names"] = "dummy"
        super()._init_options(kwargs)

        try:
            if float(self.api_version) < 38.0:
                raise TaskOptionsError("This task requires API version 38.0 or later.")
        except ValueError:
            raise TaskOptionsError(f"Invalid API version {self.api_version}")

        if "picklists" not in self.options:
            raise TaskOptionsError("The 'picklists' option is required.")

        self.picklists = defaultdict(list)
        for pl in process_list_arg(self.options["picklists"]):
            try:
                obj, field = pl.split(".")
            except ValueError:
                raise TaskOptionsError(
                    f"Picklist {pl} is not a valid Object.Field reference"
                )
            if not field.endswith("__c"):
                raise TaskOptionsError(
                    "This task only supports custom fields. To modify "
                    "Standard Value Sets, use the add_standard_value_set_entries task."
                )

            self.picklists[self._inject_namespace(obj)].append(
                self._inject_namespace(field)
            )

        if not all(["fullName" in entry for entry in self.options["entries"]]):
            raise TaskOptionsError(
                "The 'fullName' key is required on all picklist values."
            )

        if (
            sum(
                1
                for x in self.options["entries"]
                if process_bool_arg(x.get("default", False))
            )
            > 1
        ):
            raise TaskOptionsError("Only one default picklist value is allowed.")

        self.options["record_types"] = [
            self._inject_namespace(x)
            for x in process_list_arg(self.options.get("record_types", []))
        ]

        self.api_names = set(self.picklists.keys())

    def _transform_entity(self, metadata: MetadataElement, api_name: str):
        for pl in self.picklists[api_name]:
            self._modify_picklist(metadata, api_name, pl)

        return metadata

    def _modify_picklist(self, metadata: MetadataElement, api_name: str, picklist: str):
        # Locate the <fields> entry for this picklist.
        field = metadata.find("fields", fullName=picklist)

        if not field:
            raise TaskOptionsError(f"The field {api_name}.{picklist} was not found.")

        vsd = field.valueSet.find("valueSetDefinition")
        if not vsd:
            raise TaskOptionsError(
                f"The picklist {api_name}.{picklist} uses a Global Value Set, which is not supported."
            )

        # Update each entry in this picklist, and also add to all record types.
        for entry in self.options["entries"]:
            self._add_picklist_field_entry(vsd, api_name, picklist, entry)

            if self.options["record_types"]:
                self._add_record_type_entries(metadata, api_name, picklist, entry)

    def _add_picklist_field_entry(
        self, vsd: MetadataElement, api_name: str, picklist: str, entry: Dict
    ):
        fullName = entry["fullName"]
        label = entry.get("label") or fullName
        default = entry.get("default", False)
        add_before = entry.get("add_before")

        if vsd.find("value", fullName=fullName):
            self.logger.warning(
                f"Picklist entry with fullName {fullName} already exists on picklist {picklist}."
            )
        else:
            if add_before and vsd.find("value", fullName=add_before):
                entry_element = vsd.insert_before(
                    vsd.find("value", fullName=add_before), "value"
                )
            else:
                entry_element = vsd.append("value")
            entry_element.append("fullName", text=fullName)
            entry_element.append("label", text=label)
            entry_element.append("default", text=str(default).lower())

        # If we're setting this as the default, unset all of the other entries.
        if default:
            for value in vsd.findall("value"):
                default = value.find("default")
                if default:
                    default.text = (
                        "false" if value.fullName.text != fullName else "true"
                    )

    def _add_record_type_entries(
        self, metadata: MetadataElement, api_name: str, picklist: str, entry: Dict
    ):
        if "*" in self.options["record_types"]:
            rt_list = metadata.findall("recordTypes")
        else:
            rt_list = [
                metadata.find("recordTypes", fullName=record_type)
                for record_type in self.options["record_types"]
            ]

        for rt_element in rt_list:
            # Silently ignore record types that don't exist in the target org.
            if rt_element:
                self._add_single_record_type_entries(
                    rt_element, api_name, picklist, entry
                )

    def _add_single_record_type_entries(
        self, rt_element: MetadataElement, api_name: str, picklist: str, entry: Dict
    ):
        # Locate, or add, the root picklistValues element for this picklist.
        picklist_element = rt_element.find(
            "picklistValues", picklist=picklist
        ) or rt_element.append("picklistValues")
        if not picklist_element.find("picklist", text=picklist):
            picklist_element.append("picklist", text=picklist)

        # If this picklist value entry is not already present, add it.
        default = str(process_bool_arg(entry.get("default", False))).lower
        fullName = entry["fullName"]

        # The Metadata API's behavior with picklist values in record types
        # is to return partially URL-encoded values. Most punctuation appears
        # to be escaped, but spaces and high-bit characters are not.
        # To route around this, we compare the `unquote()`-ed
        # value of each element, since we don't know in 100% of cases
        # how to make our input look like what MDAPI returns.

        # Note that this behavior is different from picklist values in value sets.
        def find_matching_value(picklist, target):
            return next(
                filter(
                    lambda x: unquote(x.fullName.text) == target,
                    picklist.findall("values"),
                ),
                None,
            )

        values = find_matching_value(picklist_element, fullName)
        if not values:
            add_before = entry.get("add_before")
            if add_before:
                before_elem = find_matching_value(picklist_element, add_before)
                if before_elem:
                    values = picklist_element.insert_before(before_elem, "values")
                else:
                    values = picklist_element.append("values")
            else:
                values = picklist_element.append("values")

            # The Metadata API does _not_ require us to perform its partial URL-encoding to deploy.
            values.append("fullName", text=fullName)
            values.append("default", text=str(default).lower())

        # If this picklist value needs to be made default, remove any existing default.
        if default:
            # Find existing default and remove it, while setting our value as default
            for value in picklist_element.values:
                default = value.find("default")
                if default:
                    default.text = (
                        "false" if value.fullName.text != fullName else "true"
                    )
