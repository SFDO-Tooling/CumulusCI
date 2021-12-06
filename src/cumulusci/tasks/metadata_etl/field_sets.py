from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement


class AddFieldsToFieldSet(MetadataSingleEntityTransformTask):
    entity = "CustomObject"
    task_options = {
        "field_set": {
            "description": "Name of field set to affect, in Object__c.FieldSetName form.",
            "required": True,
        },
        "fields": {
            "description": "Array of field API names to add to the field set. "
            "Can include related fields using AccountId.Name or Lookup__r.CustomField__c style syntax.",
            "required": True,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _init_options(self, kwargs):
        self.task_config.options["api_names"] = "dummy"
        super()._init_options(kwargs)
        self.api_names = set(
            [self._inject_namespace(self.options["field_set"].split(".")[0])]
        )

        if not self.options.get("fields"):
            raise TaskOptionsError("The 'fields' option is required.")

        self.fields = []
        for field in process_list_arg(self.options["fields"]):
            self.fields.append(self._inject_namespace(field))

        self.field_set_name = self._inject_namespace(
            self.options["field_set"].split(".")[1]
        )

    def _transform_entity(self, metadata: MetadataElement, api_name: str):
        # Locate the <fieldSets> entry for this field_set.
        field_set = metadata.find("fieldSets", fullName=self.field_set_name)
        if not field_set:
            raise TaskOptionsError(
                f"The field set {self.field_set_name} was not found."
            )

        for field_name in self.fields:
            self._add_field(field_set, field_name)

        return metadata

    def _add_field(self, field_set: MetadataElement, field_name: str):

        # remove it from available fields if it's there
        available_field = field_set.find("availableFields", field=field_name)
        if available_field:
            field_set.remove(available_field)

        # check if it's already in displayedFields
        displayed_field = field_set.find("displayedFields", field=field_name)
        if displayed_field:
            self.logger.info(
                f"The field {field_name} is already in field set {self.field_set_name}."
            )
        else:
            new_field = field_set.append("displayedFields")
            new_field.append("field", text=field_name)
            new_field.append("isFieldManaged", text="false")
            new_field.append("isRequired", text="false")
