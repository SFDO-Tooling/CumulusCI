from lxml import etree

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import (
    MetadataSingleEntityTransformTask,
    get_new_tag_index,
    MD,
)


class AddPermissionSetPermissions(MetadataSingleEntityTransformTask):
    entity = "PermissionSet"
    task_options = {
        "field_permissions": {
            "description": "Array of fieldPermissions objects to upsert into permission_set.  Each fieldPermission requires the following attributes: 'field': API Name of the field including namespace; 'readable': boolean if field can be read; 'editable': boolean if field can be edited",
            "required": False,
        },
        "class_accesses": {
            "description": "Array of classAccesses objects to upsert into permission_set.  Each classAccess requires the following attributes: 'apexClass': Name of Apex Class.  If namespaced, make sure to use the form \"namespace__ApexClass\"; 'enabled': boolean if the Apex Class can be accessed.",
            "required": False,
        },
        **MetadataSingleEntityTransformTask.task_options,
    }

    def _transform_entity(self, metadata, api_name):
        self._upsert_class_accesses(metadata, api_name)
        self._upsert_field_permissions(metadata, api_name)
        return metadata

    def _upsert_class_accesses(self, metadata, api_name):
        class_accesses = self.options.get("class_accesses")

        if not class_accesses:
            return

        self.logger.info(f"Upserting class accesses for {api_name}")

        new_permission_index = get_new_tag_index(metadata, "classAccesses")

        for class_access in class_accesses:
            if "apexClass" not in class_access:
                raise TaskOptionsError(
                    "class_access entries must contain the 'apexClass' key."
                )

            class_access["apexClass"] = self._inject_namespace(
                class_access["apexClass"]
            )

            existing_permissions = metadata.findall(
                f".//{MD}classAccesses[{MD}apexClass='{class_access['apexClass']}']"
            )
            if 0 < len(existing_permissions):
                # Permission exists: update
                for elem in existing_permissions:
                    elem.find(f"{MD}enabled").text = str(
                        class_access.get("enabled", True)
                    ).lower()
            else:
                # Permission doesn't exist: insert
                elem = etree.Element(f"{MD}classAccesses")
                metadata.getroot().insert(new_permission_index, elem)

                elem_apexClass = etree.SubElement(elem, f"{MD}apexClass")
                elem_apexClass.text = class_access.get("apexClass")

                elem_enabled = etree.SubElement(elem, f"{MD}enabled")
                elem_enabled.text = str(class_access.get("enabled", True)).lower()

    def _upsert_field_permissions(self, metadata, api_name):
        field_permissions = self.options.get("field_permissions")

        if not field_permissions:
            return

        self.logger.info(f"Upserting Field Level Security for {api_name}")

        new_permission_index = get_new_tag_index(metadata, "fieldPermissions")

        for field_permission in field_permissions:
            if "field" not in field_permission:
                raise TaskOptionsError(
                    "field_permissions entries must include the 'field' key."
                )

            field_permission["field"] = self._inject_namespace(
                field_permission["field"]
            )

            existing_permissions = metadata.findall(
                f".//{MD}fieldPermissions[{MD}field='{field_permission['field']}']"
            )
            if 0 < len(existing_permissions):
                # Permission exists: update
                for elem in existing_permissions:
                    elem.find(f"{MD}readable").text = str(
                        field_permission.get("readable", True)
                    ).lower()
                    elem.find(f"{MD}editable").text = str(
                        field_permission.get("editable", True)
                    ).lower()
            else:
                # Permission doesn't exist: insert
                elem = etree.Element(f"{MD}fieldPermissions")
                metadata.getroot().insert(new_permission_index, elem)

                elem_field = etree.SubElement(elem, f"{MD}field")
                elem_field.text = field_permission.get("field")

                elem_editable = etree.SubElement(elem, f"{MD}editable")
                elem_editable.text = str(field_permission.get("editable", True)).lower()

                elem_readable = etree.SubElement(elem, f"{MD}readable")
                elem_readable.text = str(field_permission.get("readable", True)).lower()
