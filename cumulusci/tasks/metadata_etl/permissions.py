import typing as T

import pydantic.v1 as pydantic

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata_etl import MetadataSingleEntityTransformTask
from cumulusci.utils.xml.metadata_tree import MetadataElement


class IPRange(pydantic.BaseModel):
    description: T.Optional[str]
    start_address: pydantic.IPvAnyAddress
    end_address: pydantic.IPvAnyAddress


class IPNetwork(pydantic.BaseModel):
    description: T.Optional[str]
    network: pydantic.IPvAnyNetwork


class AddIPRangesOptions(pydantic.BaseModel):
    ranges: T.List[T.Union[IPRange, IPNetwork]]
    replace: bool = False


class AddIPRanges(MetadataSingleEntityTransformTask):
    entity = "Profile"
    task_options = {
        "ranges": {
            "description": "A list of IP ranges, specified as dicts with the keys 'description' (optional) and either 'start_address' and 'end_address' or 'network' (in CIDR notation).",
            "required": True,
        },
        "replace": {
            "description": "If True, replace all existing ranges. Otherwise, just add ranges. Default is False."
        },
    }

    def _transform_entity(
        self, metadata: MetadataElement, api_name: str
    ) -> MetadataElement:
        try:
            opts = AddIPRangesOptions.parse_obj(self.options)
        except pydantic.ValidationError as exc:
            raise TaskOptionsError(f"Invalid options: {exc}")

        if opts.replace:
            # Remove existing ranges
            for elem in metadata.findall("loginIpRanges"):
                metadata.remove(elem)

        for ip_range in opts.ranges:
            if isinstance(ip_range, IPNetwork):
                elem = metadata.append("loginIpRanges")
                elem.append("description", text=ip_range.description or "")
                elem.append(
                    "startAddress", text=str(ip_range.network.network_address + 1)
                )
                elem.append(
                    "endAddress", text=str(ip_range.network.broadcast_address - 1)
                )
            else:
                elem = metadata.append("loginIpRanges")
                elem.append("description", text=ip_range.description or "")
                elem.append("startAddress", text=str(ip_range.start_address))
                elem.append("endAddress", text=str(ip_range.end_address))

        return metadata


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

    def _transform_entity(
        self, metadata: MetadataElement, api_name: str
    ) -> MetadataElement:
        self._upsert_class_accesses(metadata, api_name)
        self._upsert_field_permissions(metadata, api_name)
        return metadata

    def _upsert_class_accesses(self, metadata, api_name):
        class_accesses = self.options.get("class_accesses")

        if not class_accesses:
            return

        self.logger.info(f"Upserting class accesses for {api_name}")

        for class_access in class_accesses:
            if "apexClass" not in class_access:
                raise TaskOptionsError(
                    "class_access entries must contain the 'apexClass' key."
                )

            class_access["apexClass"] = self._inject_namespace(
                class_access["apexClass"]
            )

            existing_permissions = metadata.findall(
                "classAccesses", apexClass=class_access["apexClass"]
            )

            if len(existing_permissions):
                # Permission exists: update
                for elem in existing_permissions:
                    elem.find("enabled").text = str(
                        class_access.get("enabled", True)
                    ).lower()
            else:
                # Permission doesn't exist: insert
                elem = metadata.append("classAccesses")
                elem.append("apexClass", text=class_access.get("apexClass"))
                elem.append(
                    "enabled", text=str(class_access.get("enabled", True)).lower()
                )

    def _upsert_field_permissions(self, metadata, api_name):
        field_permissions = self.options.get("field_permissions")

        if not field_permissions:
            return

        self.logger.info(f"Upserting Field Level Security for {api_name}")

        for field_permission in field_permissions:
            if "field" not in field_permission:
                raise TaskOptionsError(
                    "field_permissions entries must include the 'field' key."
                )

            field_permission["field"] = self._inject_namespace(
                field_permission["field"]
            )

            existing_permissions = metadata.findall(
                "fieldPermissions", field=field_permission["field"]
            )

            if len(existing_permissions):
                # Permission exists: update
                for elem in existing_permissions:
                    elem.find("readable").text = str(
                        field_permission.get("readable", True)
                    ).lower()
                    elem.find("editable").text = str(
                        field_permission.get("editable", True)
                    ).lower()
            else:
                # Permission doesn't exist: insert
                element = metadata.append("fieldPermissions")
                element.append("field", text=field_permission.get("field"))
                element.append(
                    "editable", text=str(field_permission.get("editable", True)).lower()
                )
                element.append(
                    "readable", text=str(field_permission.get("readable", True)).lower()
                )
