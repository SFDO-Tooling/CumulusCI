from collections import defaultdict
from datetime import datetime

import os
import yaml
import pytest

from cumulusci.tasks.metadata_etl.base import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement
from cumulusci.utils import os_friendly_path
from cumulusci.utils.xml import metadata_tree
from cumulusci.tasks.bulkdata.generate_mapping import GenerateMapping
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError


class EncryptAllFields(MetadataSingleEntityTransformTask):

    entity = "CustomObject"

    default_blocklist_path = "unencryptable.yml"

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
            "description": "The path to a YAML settings file of Object.Field entities known to be unencrpytable. "
            "Defaults to unencryptable.yml. Custom entities must be namespace tokenized."
        },
        "timeout": {
            "description": "The max amount of time to wait in seconds. Defaults to 60.",
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.options["timeout"] = int(self.options.get("timeout", 90))
        self.blocklist_path = os_friendly_path(
            self.options.get("blocklist_path")
            if self.options.get("blocklist_path")
            else self.default_blocklist_path
        )

    def _run_task(self):
        self._set_blocklist()

        standard_object_allowlist_path = os.path.join(
            os.path.dirname(__file__), "encryptable_standard_schema.yml"
        )
        with open(standard_object_allowlist_path, "r") as f:
            self.standard_object_allowlist = yaml.safe_load(f)
            # TODO: check that admin has FLS for each field
            # if they don't, log an error and remove it from the list
            # getattr(self.sf, sobject_api_name).describe()["fields"]

        self._set_api_names()

        self.fields_to_encrypt = defaultdict(list)

        super()._run_task()

    def _set_blocklist(self):
        if os.path.isfile(self.blocklist_path):
            with open(self.blocklist_path, "r") as f:
                self.logger.info(f"Using blocklist provided at {self.blocklist_path}")
                content = f.read()
                content = self._inject_namespace(content)
                self.blocklist = yaml.safe_load(content)
        elif "blocklist_path" in self.options:
            raise TaskOptionsError(f"No blocklist found at {self.blocklist_path}.")
        else:
            self.logger.info(
                f"No blocklist found at {self.blocklist_path}. Attempting to encrypt all fields."
            )
            self.blocklist = {}

    def _set_api_names(self):
        self.api_names = {
            sobject["name"]
            for sobject in self.sf.describe()["sobjects"]
            if (
                # ChangeEvents and CustomSettings are sobjects but we can filter them out as non-encryptable
                not (sobject["name"].endswith("ChangeEvent"))
                and not sobject["customSetting"]
                and (
                    # custom objects
                    sobject["name"].endswith("__c")
                    # standard objects that have encryptable fields
                    or sobject["name"] in self.standard_object_allowlist.keys()
                    # standard objects that have custom fields
                    or any(
                        field["name"].endswith("__c")
                        for field in getattr(self.sf, sobject["name"]).describe()[
                            "fields"
                        ]
                    )
                )
            )
        }

    def _is_in_standard_object_allowlist(self, object_api_name, field_api_name):
        # allowlist is dict: object_api_name -> list of field_api_names
        return self.standard_object_allowlist.get(
            object_api_name
        ) and field_api_name in self.standard_object_allowlist.get(object_api_name)

    def _is_in_blocklist(self, object_api_name, field_api_name):
        # blocklist is dict: object_api_name -> list of field_api_names
        return False if not self.blocklist else self.blocklist.get(
            object_api_name
        ) and field_api_name in self.blocklist.get(object_api_name)

    def _is_encryptable(self, object_api_name, field):
        field_api_name = field.fullName.text
        return (
            (
                # all custom fields - on both standard objects and custom objects
                field_api_name.endswith("__c")
                and field.type.text in self.encryptable_field_types
                and not field.find("formula")
            )
            or (
                # standard fields on standard objects
                self._is_in_standard_object_allowlist(object_api_name, field_api_name)
            )
        ) and not self._is_in_blocklist(object_api_name, field_api_name)

    def encrypt_field(self, field: MetadataElement):
        if field.find("encryptionScheme"):
            if field.encryptionScheme.text == "DeterministicEncryption":
                raise CumulusCIException(
                    f"This org is already using DeterministicEncryption."
                )
            elif field.encryptionScheme.text == "None":
                field.encryptionScheme.text = "ProbabilisticEncryption"

    def _transform_entity(self, custom_object: MetadataElement, object_api_name: str):
        dirty_object = False

        # MD Api bug https://gus.lightning.force.com/lightning/r/ADM_Work__c/a07B0000008lxMBIAY/view
        existing_list_views = custom_object.findall("listViews")
        for lv in existing_list_views:
            custom_object.remove(lv)
            
        # special handling required for custom object Name fields, as they don't live in a "fields" tag
        if object_api_name.endswith("__c") and not self._is_in_blocklist(
            object_api_name, "Name"
        ):
            name_field = custom_object.find("nameField")
            if name_field.find("encryptionScheme"):
                # print('BEFORE*****')
                # print(name_field.tostring())
                self.encrypt_field(name_field)
                # print('AFTER******')
                # print(name_field.tostring())
                self.fields_to_encrypt[object_api_name].append("Name")
                dirty_object = True

        for field in custom_object.findall("fields"):
            if self._is_encryptable(object_api_name, field):
                self.encrypt_field(field)
                self.fields_to_encrypt[object_api_name].append(field.fullName.text)
                dirty_object = True

        return custom_object if dirty_object else None

    def _post_deploy(self, result):
        if result == "Success":
            super()._post_deploy(result)
            self.logger.info("Waiting for encrypytion enablement to complete.")
            self.time_start = datetime.now()
            self._poll()

    def _poll_action(self):
        elapsed = datetime.now() - self.time_start
        if elapsed.total_seconds() > self.options["timeout"]:
            for sobject_api_name in self.fields_to_encrypt.keys():
                if self.fields_to_encrypt[sobject_api_name]:
                    self.logger.warn(
                        f"Couldn't encrypt: {sobject_api_name} fields {self.fields_to_encrypt[sobject_api_name]}"
                    )
            raise CumulusCIException(
                (
                    f'Encryption enablement not successfully completed after {self.options["timeout"]} seconds.'
                )
            )

        for sobject_api_name in self.fields_to_encrypt.keys():
            field_map = {
                field["name"]: field
                for field in getattr(self.sf, sobject_api_name).describe()["fields"]
                if field["name"] in self.fields_to_encrypt[sobject_api_name]
            }

            fields_to_remove = []

            for field_api_name in self.fields_to_encrypt[sobject_api_name]:
                if not field_map[field_api_name]["filterable"]:
                    fields_to_remove.append(field_api_name)

            for field_api_name in fields_to_remove:
                self.fields_to_encrypt[sobject_api_name].remove(field_api_name)

        if not any(self.fields_to_encrypt.values()):
            self.logger.info(
                (f"Platform Encryption enablement successfully completed! 🛡")
            )
            self.poll_complete = True
        else:
            return
