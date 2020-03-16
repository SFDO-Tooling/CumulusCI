from typing import List, Dict, Any
import json
from pathlib import Path

from pydantic import Field, create_model

from cumulusci.utils.yaml.model_parser import CCIDictModel
from cumulusci.core.utils import process_list_of_pairs_dict_arg


def _describe_field(field):
    "Convert a Pydantic field into a CCI task_option dict"
    rc = {
        "description": field.field_info.description,
        "required": field.required,
    }
    if field.field_info.default != ...:
        rc["default"] = field.field_info.default
    return rc


class CCIOptions(CCIDictModel):
    @classmethod
    def as_task_options(cls):
        return {
            fieldname: _describe_field(field)
            for fieldname, field in cls.__fields__.items()
        }


class CCIOptionType:
    name = None

    @classmethod
    def __get_validators__(cls):
        "https://pydantic-docs.helpmanual.io/usage/types/#classes-with-__get_validators__"
        yield cls.validate

    @classmethod
    def validate(cls, v):
        """Validate and convert a value.

        If its a string, parse it, else, just validate it.
        """
        if isinstance(v, str):
            if v.startswith("{") or v.startswith("["):
                v = json.loads(v)
            else:
                v = cls.from_str(v)

        # Pydantic can't just parse/validate arbitrary data unless
        # it has a model. So we create a dummy model for
        # it to have a parsing/validating context
        Dummy = create_model(cls.name or cls.__name__, __root__=(cls.target_type, ...))

        return Dummy.parse_obj(v).__root__


class ListOfStringsOption(CCIOptionType):
    """Parses a list of strings from a string"""

    target_type = List[str]

    @classmethod
    def from_str(cls, v):
        return [s.strip() for s in v.split(",")]


class PathOption(CCIOptionType):
    """Parses a Path from a string"""

    target_type = Path

    @classmethod
    def from_str(cls, v):
        return Path(v)


class MappingOption(CCIOptionType):
    """Parses a Mapping of Str->Any from a string"""

    target_type = Dict[str, Any]

    @classmethod
    def from_str(cls, v):
        return process_list_of_pairs_dict_arg(v)


Field = Field  # export this and shut up linter
