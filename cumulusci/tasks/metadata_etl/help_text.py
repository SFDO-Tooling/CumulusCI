from collections import defaultdict

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement
from cumulusci.core.utils import process_list_arg


class AddHelpText(MetadataSingleEntityTransformTask):
    entity = "CustomObject"
    task_options = {
        "entries": {
            "description": "List of custom object fields to affect, in Object__c.Field__c form.",
            "required": True,
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

        if "entries" not in self.options:
            raise TaskOptionsError(
                "The 'entries' option is required, please pass a dictionary with the object_field and help_text keys."
            )
        if type(self.options["entries"]) != list or len(self.options["entries"]) == 0:
            raise TaskOptionsError(
                "Please populate the entries field with a list of dictionaries containing at minimum one entry with an 'object_field' and 'help_text' keys"
            )
        if not all(["object_field" in entry for entry in self.options["entries"]]):
            raise TaskOptionsError(
                "The 'object_field' key is required on all entry values."
            )
        if not all(["help_text" in entry for entry in self.options["entries"]]):
            raise TaskOptionsError(
                "The 'help_text' key is required on all entry values to declare what help text value to insert."
            )
        self.object_fields = defaultdict(list)
        for entry in process_list_arg(self.options["entries"]):
            try:
                obj, field = entry["object_field"].split(".")
                if not field.endswith("__c"):
                    raise TaskOptionsError(
                        "This task only supports custom fields. To modify "
                        "Standard Value Sets, use the add_standard_value_set_entries task."
                    )
                self.object_fields[self._inject_namespace(obj)].append(
                    (self._inject_namespace(field), entry["help_text"])
                )
            except ValueError:
                raise TaskOptionsError(
                    f"object_field {entry} is not a valid Object.Field reference"
                )

        self.api_names = set(self.object_fields.keys())

    def _transform_entity(self, metadata: MetadataElement, api_name: str):
        for entry in self.object_fields[api_name]:
            self._modify_help_text(metadata, api_name, entry[0], entry[1])
        return metadata

    def _modify_help_text(
        self,
        metadata: MetadataElement,
        api_name: str,
        custom_field: str,
        help_text: str,
    ):
        # Locate the <fields> entry for this field entry.
        field = metadata.find("fields", fullName=custom_field)
        if not field:
            raise TaskOptionsError(
                f"The field {api_name}.{custom_field} was not found."
            )
        try:
            field.inlineHelpText.text = help_text
        except AttributeError:
            print("there")
            field.append("inlineHelpText", text=help_text)
