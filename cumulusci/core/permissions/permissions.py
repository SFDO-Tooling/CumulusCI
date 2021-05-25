from typing import Any, List, Dict, Optional
from enum import Enum
from cumulusci.utils.yaml.model_parser import CCIDictModel


class SystemPermOption(str, Enum):
    user_permissions = "user_permissions"
    custom_applications = "custom_applications"
    apex_classes = "apex_classes"
    custom_metadata_types = "custom_metadata_types"
    custom_settings = "custom_settings"
    custom_permissions = "custom_permissions"
    data_sources = "data_sources"
    flows = "flows"
    visualforce_pages = "visualforce_pages"
    custom_tabs = "custom_tabs"


class PermObject(CCIDictModel):
    create: bool = False
    read: bool = False
    edit: bool = False
    delete: bool = False
    view_all: bool = False
    modify_all: bool = False
    default: Optional[bool] = None


class PermField(CCIDictModel):
    read: bool = False
    edit: bool = False


class SchemaDefault(CCIDictModel):
    object_permission: PermObject
    field_permission: PermField


class SchemaObject(PermObject):
    fields: Dict[str, PermField] = None


# Adding new root node to limit what is available. Is this too restrictive?
class PermissionRoot(CCIDictModel):
    # Add new root node ?
    metadata: Dict[SystemPermOption, List[str]] = {}
    # SchemaDefault || SchemaObject
    schema: Dict[str, Any] = {}
