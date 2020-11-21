import os
import yaml

from cumulusci.tasks.metadata_etl.base import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement
from cumulusci.utils import os_friendly_path
from cumulusci.utils.xml import metadata_tree

# from cumulusci.utils import process_list_arg


class EncryptAllFields(MetadataSingleEntityTransformTask):

    entity = "CustomObject"

    encryptable_field_types = [
        "Email",
        "Phone",
        "Url",
        "Text",
        "Date",
        "DateTime",
        "LongTextArea",
    ]

    task_options = {
        "blocklist_path": {
            "description": "The path to a YAML settings file of Object.Field entities known to be unencrpytable.",
            "required": False,
        }
    }

    def _init_options(self, kwargs):
        self.task_config.options["api_names"] = "dummy"
        super()._init_options(kwargs)

        # inline list option version
        # self.blocklist_path = process_list_arg(self.options.get("blocklist", []))

        # yml file path version
        self.blocklist_path = os_friendly_path(self.options.get("blocklist_path"))
        if self.blocklist_path is None or not os.path.isfile(self.blocklist_path):
            raise TaskOptionsError(f"File {self.blocklist_path} does not exist")
        print(self.blocklist_path)

    def _run_task(self):
        with open(self.blocklist_path, "r") as f:
            ## TODO: namespace inject this contents based on tokens in the yml
            content = f.read()
            content = self._inject_namespace(content)
            self.blocklist = yaml.safe_load(content)

        base_path = os.path.dirname(__file__)
        mapping_path = os.path.join(base_path, "encryptable_standard_schema.yml")
        with open(mapping_path, "r") as f:
            self.standard_object_allowlist = yaml.safe_load(f)

        # self.api_names also needs to include the standard objects that have encryptable fields
        # self.api_names also needs standard objects that don't have standard encryptable fields but do have custom fields
        self.api_names = [
            sobject["name"]
            for sobject in self.sf.describe()["sobjects"]
            if (
                sobject["name"].endswith("__c")
                or sobject["name"] == "Account"
                or sobject["name"] == "Contact"
            )
            and not sobject["customSetting"]
        ]

        super()._run_task()

    def _is_in_standard_object_allowlist(self, object_api_name, field_api_name):
        # allowlist is dict: object_api_name -> list of field_api_names
        return self.standard_object_allowlist.get(
            object_api_name
        ) and field_api_name in self.standard_object_allowlist.get(object_api_name)

    def _is_in_blocklist(self, object_api_name, field_api_name):
        # blocklist is dict: object_api_name -> list of field_api_names
        return self.blocklist.get(
            object_api_name
        ) and field_api_name in self.blocklist.get(object_api_name)

    def _is_encryptable(self, object_api_name, field):
        field_api_name = field.fullName.text
        return (
            (
                # all custom fields - on both standard objects and custom objects
                field_api_name.endswith("__c")
                and field.type.text in self.encryptable_field_types
            )
            or (
                # standard fields on standard objects
                self._is_in_standard_object_allowlist(object_api_name, field_api_name)
            )
        ) and not self._is_in_blocklist(object_api_name, field_api_name)

    def encrypt_field(self, field: MetadataElement):
        if field.find("encryptionScheme"):
            if field.encryptionScheme.text == "DeterministicEncryption":
                self.logger.error(f"This org is already using DeterministicEncryption.")
            elif field.encryptionScheme.text == "None":
                field.encryptionScheme.text = "ProbabilisticEncryption"

    def _transform_entity(self, custom_object: MetadataElement, object_api_name: str):
        dirty_object = False

        # special handling required for custom object Name fields, as they don't live in a "fields" tag
        if object_api_name.endswith("__c"):
            name_field = custom_object.find("nameField")
            self.encrypt_field(name_field)
            dirty_object = True

        for field in custom_object.findall("fields"):
            if self._is_encryptable(object_api_name, field):
                self.encrypt_field(field)
                dirty_object = True

        if dirty_object:
            print(custom_object.tostring())

        return custom_object if dirty_object else None
