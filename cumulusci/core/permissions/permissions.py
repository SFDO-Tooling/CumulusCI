from typing import List, Dict, Optional, Union
from cumulusci.utils.yaml.model_parser import CCIModel

from pydantic import Field, validator


class MetadataPermission(CCIModel):
    # Optional root level class. Do these need to be accounted for?
    data: List[str]


class PermissionsSobject(CCIModel):
    create: bool = False
    read: bool = False
    edit: bool = False
    delete: bool = False
    view_all: bool = False
    modify_all: bool = False
    default: Optional[str] = None


class PermField(CCIModel):
    read: bool = False
    edit: bool = False


class SchemaDefaultDetail(CCIModel):
    object_permissions: PermissionsSobject
    field_permissions: PermField


class SchemaSobject(PermissionsSobject):
    fields_: Dict[str, PermField] = Field({}, alias="fields")

    # Profile Properties
    record_types: List[str] = []
    unmanaged_record_types: List[str] = []
    default_record_type: Optional[str]
    default_person_account_record_type: Optional[str]

    @validator("fields_")
    def defaults_typo_check(cls, fields_):
        if "defaults" in fields_:
            raise ValueError('Did you mean "default"?')
        return fields_


class Schema(CCIModel):
    defaults: Optional[Dict[str, SchemaDefaultDetail]]
    sobjects: Dict[str, SchemaSobject]


# Adding new root node to limit what is available. Is this too restrictive?
class PermissionsRoot(CCIModel):

    apex_classes: List[str]
    user_permissions: List[str]
    custom_applications: List[str]
    custom_metadata_types: List[str]
    custom_permissions: List[str]
    custom_settings: List[str]
    custom_tabs: List[str]
    data_sources: List[str]
    flows: List[str]
    visualforce_pages: List[str]

    schema_: Schema = Field({}, alias="schema")


class PermissionsFile(CCIModel):
    __root__: Union[PermissionsRoot, None]
