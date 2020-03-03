from typing import Dict, List

from pydantic import Field


from cumulusci.utils.yaml.model_parser import MappingBaseModel


class Lookup(MappingBaseModel):
    table: str
    key_field: str = None
    value_field: str = None
    join_field: str = None
    after: str = None
    aliased_table: str = None


class Step(MappingBaseModel):
    sf_object: str
    table: str = None
    fields_: Dict[str, str] = Field(..., alias="fields")
    lookups: Dict[str, Lookup] = {}
    static: Dict[str, str] = {}
    filters: List[str] = []
    action: str = "insert"
    oid_as_pk: bool = False  # this one should be discussed and probably deprecated
    record_type: str = None  # should be discussed and probably deprecated


class MappingSteps(MappingBaseModel):
    __root__: Dict[str, Step]


def parse_mapping_from_yaml(source):
    return MappingSteps.parse_from_yaml(source).__root__
