from typing import Dict, List, Union, IO
from logging import getLogger
from pathlib import Path

from pydantic import Field, validator, ValidationError

from cumulusci.utils.yaml.model_parser import CCIDictModel
from typing_extensions import Literal

LOGGER_NAME = "MAPPING_LOADER"
logger = getLogger(LOGGER_NAME)


class MappingLookup(CCIDictModel):
    "Lookup relationship between two tables."
    table: str
    key_field: str = None
    value_field: str = None
    join_field: str = None
    after: str = None
    aliased_table: str = None


class MappingStep(CCIDictModel):
    "Step in a load or extract process"
    sf_object: str
    table: str = None
    fields_: Dict[str, str] = Field(..., alias="fields")
    lookups: Dict[str, MappingLookup] = {}
    static: Dict[str, str] = {}
    filters: List[str] = []
    action: str = "insert"
    oid_as_pk: bool = False  # this one should be discussed and probably deprecated
    record_type: str = None  # should be discussed and probably deprecated
    bulk_mode: Literal["Serial", "Parallel"] = "Parallel"

    @validator("record_type")
    def record_type_is_deprecated(cls, v):
        logger.warning(
            "record_type is deprecated. Just supply a RecordTypeId column declaration and it will be inferred"
        )
        return v

    @validator("oid_as_pk")
    def oid_as_pk_is_deprecated(cls, v):
        logger.warning(
            "oid_as_pk is deprecated. Just supply an Id column declaration and it will be inferred."
        )
        return v


class MappingSteps(CCIDictModel):
    "Mapping of named steps"
    __root__: Dict[str, MappingStep]


ValidationError = ValidationError  # export Pydantic's Validation Error under an alias


def parse_from_yaml(source: Union[str, Path, IO]) -> Dict:
    "Parse from a path, url, path-like or file-like"
    return MappingSteps.parse_from_yaml(source)
