import xml.etree.ElementTree as XML_ET

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.metadata_etl import (
    MetadataSingleEntityTransformTask,
    get_new_tag_index,
)


class AddPermissions(MetadataSingleEntityTransformTask):
    entity = "PermissionSet"
    task_options = {
        "field_permissions": {
            "description": "Array of fieldPermissions objects to upsert into permission_set.  Each fieldPermission requires the following attributes: 'field': API Name of the field including namespace; 'readable': boolean if field can be read; 'editable': boolean if field can be edited",
            "required": "False",
        },
        "class_accesses": {
            "description": "Array of classAccesses objects to upsert into permission_set.  Each classAccess requires the following attributes: 'apexClass': Name of Apex Class.  If namespaced, make sure to use the form \"namespace__ApexClass\"; 'enabled': boolean if the Apex Class can be accessed.",
            "required": "False",
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

        new_permission_index = get_new_tag_index(
            metadata, "classAccesses", self.namespaces
        )

        for class_access in class_accesses:
            if "apexClass" not in class_access:
                raise TaskOptionsError(
                    "class_access entries must contain the 'apexClass' key."
                )

            class_access["apexClass"] = self._namespace_injector(
                class_access["apexClass"]
            )

            existing_permissions = metadata.findall(
                f".//sf:classAccesses[sf:apexClass='{class_access['apexClass']}']",
                self.namespaces,
            )
            if 0 < len(existing_permissions):
                # Permission exists: update
                for elem in existing_permissions:
                    elem.find("sf:enabled", self.namespaces).text = str(
                        class_access.get("enabled", True)
                    ).lower()
            else:
                # Permission doesn't exist: insert
                elem = XML_ET.Element("{%s}classAccesses" % (self.namespaces.get("sf")))
                metadata.getroot().insert(new_permission_index, elem)

                elem_apexClass = XML_ET.SubElement(
                    elem, "{%s}apexClass" % (self.namespaces.get("sf"))
                )
                elem_apexClass.text = class_access.get("apexClass")

                elem_enabled = XML_ET.SubElement(
                    elem, "{%s}enabled" % (self.namespaces.get("sf"))
                )
                elem_enabled.text = str(class_access.get("enabled", True)).lower()

    def _upsert_field_permissions(self, metadata, api_name):
        field_permissions = self.options.get("field_permissions")

        if not field_permissions:
            return

        self.logger.info(f"Upserting Field Level Security for {api_name}")

        new_permission_index = get_new_tag_index(
            metadata, "fieldPermissions", self.namespaces
        )

        for field_permission in field_permissions:
            if "field" not in field_permission:
                raise TaskOptionsError(
                    "field_permissions entries must include the 'field' key."
                )

            field_permission["field"] = self._namespace_injector(
                field_permission["field"]
            )

            existing_permissions = metadata.findall(
                f".//sf:fieldPermissions[sf:field='{field_permission['field']}']",
                self.namespaces,
            )
            if 0 < len(existing_permissions):
                # Permission exists: update
                for elem in existing_permissions:
                    elem.find("sf:readable", self.namespaces).text = str(
                        field_permission.get("readable", True)
                    ).lower()
                    elem.find("sf:editable", self.namespaces).text = str(
                        field_permission.get("editable", True)
                    ).lower()
            else:
                # Permission doesn't exist: insert
                elem = XML_ET.Element(
                    "{%s}fieldPermissions" % (self.namespaces.get("sf"))
                )
                metadata.getroot().insert(new_permission_index, elem)

                elem_field = XML_ET.SubElement(
                    elem, "{%s}field" % (self.namespaces.get("sf"))
                )
                elem_field.text = field_permission.get("field")

                elem_editable = XML_ET.SubElement(
                    elem, "{%s}editable" % (self.namespaces.get("sf"))
                )
                elem_editable.text = str(field_permission.get("editable", True)).lower()

                elem_readable = XML_ET.SubElement(
                    elem, "{%s}readable" % (self.namespaces.get("sf"))
                )
                elem_readable.text = str(field_permission.get("readable", True)).lower()
