from typing import Dict, List, Union, IO
from logging import getLogger
from pathlib import Path
from collections import defaultdict

from pydantic import Field, validator, ValidationError

from cumulusci.utils.yaml.model_parser import CCIModel, CCIDictModel
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


class MappingSteps(CCIModel):
    "Mapping of named steps"
    __root__: Dict[str, MappingStep]


class Mapping(dict):
    def __init__(self, steps):
        super().__init__(steps)

    @classmethod
    def parse_from_yaml(cls, source):
        steps = MappingSteps.parse_from_yaml(source)
        return cls(steps)

    def _expand_mapping(self, models):
        """Walk the mapping and generate any required 'after' steps
        to handle dependent and self-lookups.

        Uses the models to set up foreign-key relationships."""
        # Expand the mapping to handle dependent lookups
        self.after_steps = defaultdict(dict)

        for step in self.values():
            step["action"] = step.get("action", "insert")
            if step.get("lookups") and any(
                [l.get("after") for l in step["lookups"].values()]
            ):
                # We have deferred/dependent lookups.
                # Synthesize mapping steps for them.

                sobject = step["sf_object"]
                after_list = {
                    l["after"] for l in step["lookups"].values() if l.get("after")
                }

                for after in after_list:
                    lookups = {
                        lookup_field: lookup
                        for lookup_field, lookup in step["lookups"].items()
                        if lookup.get("after") == after
                    }
                    print("XXX", lookups)
                    name = f"Update {sobject} Dependencies After {after}"
                    mapping = {
                        "sf_object": sobject,
                        "action": "update",
                        "table": step["table"],
                        "lookups": {},
                        "fields": {},
                    }
                    mapping["lookups"]["Id"] = {
                        "table": step["table"],
                        "key_field": models[
                            step["table"]
                        ].__table__.primary_key.columns.keys()[0],
                    }
                    for l in lookups:
                        mapping["lookups"][l] = lookups[l].copy()
                        mapping["lookups"][l]["after"] = None

                    self.after_steps[after][name] = mapping


ValidationError = ValidationError  # export Pydantic's Validation Error under an alias


def parse_from_yaml(source: Union[str, Path, IO]) -> Dict:
    "Parse from a path, url, path-like or file-like"
    return Mapping.parse_from_yaml(source)
