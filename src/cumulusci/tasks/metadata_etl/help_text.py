from collections import defaultdict

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement


class SetFieldHelpText(MetadataSingleEntityTransformTask):
    entity = "CustomObject"
    task_options = {
        "fields": {
            "description": "List of object fields to affect, in Object__c.Field__c form.",
            "required": True,
        },
        "overwrite": {
            "description": "If set to True, overwrite any differing Help Text found on the field. "
            "By default, Help Text is set only if it is blank."
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        self.task_config.options["api_names"] = "dummy"
        super()._init_options(kwargs)

        self.options["overwrite"] = process_bool_arg(
            self.options.get("overwrite", False)
        )

        if (
            not isinstance(self.options.get("fields"), list)
            or len(self.options["fields"]) == 0
        ):
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
        for field, help_text in self.api_name_list[api_name]:
            self._modify_help_text(metadata, api_name, field, help_text)
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
            if (
                field.inlineHelpText.text == ""
                or field.inlineHelpText.text == help_text
                or self.options["overwrite"]
            ):
                field.inlineHelpText.text = help_text
            else:
                self.logger.warning(
                    f"Help text for field {api_name} has a different value. "
                    "Set the overwrite option to True to overwrite this field help text."
                )
        except AttributeError:
            field.append("inlineHelpText", text=help_text)
