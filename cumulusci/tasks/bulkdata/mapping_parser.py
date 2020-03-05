from typing import Dict, List
from logging import getLogger

from pydantic import Field, validator, ValidationError

from cumulusci.utils.yaml.model_parser import CCIDictModel

LOGGER_NAME = "MAPPING_LOADER"


class Lookup(CCIDictModel):
    "Lookup relationship between two tables."
    table: str
    key_field: str = None
    value_field: str = None
    join_field: str = None
    after: str = None
    aliased_table: str = None


class Step(CCIDictModel):
    "Step in a load or extract process"
    sf_object: str
    table: str = None
    fields_: Dict[str, str] = Field(..., alias="fields")
    lookups: Dict[str, Lookup] = {}
    static: Dict[str, str] = {}
    filters: List[str] = []
    action: str = "insert"
    oid_as_pk: bool = False  # this one should be discussed and probably deprecated
    record_type: str = None  # should be discussed and probably deprecated

    @validator("record_type")
    def record_type_is_deprecated(cls, v):
        getLogger(LOGGER_NAME).warning(
            "record_type is deprecated. Just supply an RecordTypeId column declaration and it will be inferred"
        )
        return v

    @validator("oid_as_pk")
    def oid_as_pk_is_deprecated(cls, v):
        getLogger(LOGGER_NAME).warning(
            "oid_as_pk is deprecated. Just supply an Id column declaration and it will be inferred."
        )
        return v


class MappingSteps(CCIDictModel):
    "Mapping of named steps"
    __root__: Dict[str, Step]


ValidationError = ValidationError  # export Pydantic's Validation Error under an alias


def parse_from_yaml(source):
    "Parse a mapping file from a YAML source."
    return MappingSteps.parse_from_yaml(source)
