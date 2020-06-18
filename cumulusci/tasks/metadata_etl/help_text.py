from collections import defaultdict

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement
from cumulusci.core.utils import process_list_arg


class SetFieldHelpText(MetadataSingleEntityTransformTask):
    entity = "CustomObject"
    task_options = {
        "fields": {
            "description": "List of object fields to affect, in Object__c.Field__c form.",
            "required": True,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        self.task_config.options["api_names"] = "dummy"
        super()._init_options(kwargs)

        try:
            float(self.api_version)
        except ValueError:
            raise TaskOptionsError(f"Invalid API version {self.api_version}")

        if "fields" not in self.options:
            raise TaskOptionsError(
                "The 'fields' option is required, please pass a dictionary with the api_name and help_text keys."
            )
        if type(self.options["fields"]) != list or len(self.options["fields"]) == 0:
            raise TaskOptionsError(
                "Please populate the fields field with a list of dictionaries containing at minimum one entry with an 'api_name' and 'help_text' keys"
            )
        if not all(["api_name" in entry for entry in self.options["fields"]]):
            raise TaskOptionsError(
                "The 'api_name' key is required on all entry values."
            )
        if not all(["help_text" in entry for entry in self.options["fields"]]):
            raise TaskOptionsError(
                "The 'help_text' key is required on all entry values to declare what help text value to insert."
            )
        self.api_name_list = defaultdict(list)
        for entry in process_list_arg(self.options["fields"]):
            try:
                obj, field = entry["api_name"].split(".")

                self.api_name_list[self._inject_namespace(obj)].append(
                    (self._inject_namespace(field), entry["help_text"])
                )
            except ValueError:
                raise TaskOptionsError(
                    f"api_name {entry} is not a valid Object.Field reference"
                )

        self.api_names = set(self.api_name_list.keys())

    def _transform_entity(self, metadata: MetadataElement, api_name: str):
        for entry in self.api_name_list[api_name]:
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
            field.append("inlineHelpText", text=help_text)
