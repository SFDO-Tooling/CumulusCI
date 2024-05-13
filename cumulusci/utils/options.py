import json
from inspect import signature
from typing import Any, Dict, List

from pydantic import DirectoryPath, Field, FilePath, create_model

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.utils.yaml.model_parser import CCIDictModel

READONLYDICT_ERROR_MSG = (
    "The 'options' dictionary is read-only. Please use 'parsed_options' instead."
)


def _describe_field(field):
    "Convert a Pydantic field into a CCI task_option dict"
    rc = {
        "description": field.field_info.description,
        "required": field.required,
    }
    if field.field_info.default != ...:
        rc["default"] = field.field_info.default
    return rc


class ReadOnlyOptions(dict):
    """To enforce self.options to be read-only"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        raise TaskOptionsError(READONLYDICT_ERROR_MSG)

    def __delitem__(self, key):
        raise TaskOptionsError(READONLYDICT_ERROR_MSG)

    def pop(self, key, default=None):
        raise TaskOptionsError(READONLYDICT_ERROR_MSG)


class CCIOptions(CCIDictModel):
    "Base class for all options in tasks"

    @classmethod
    def as_task_options(cls):
        return {
            fieldname: _describe_field(field)
            for fieldname, field in cls.__fields__.items()
        }


class CCIOptionType:
    """Base class for custom option types.

    Subclasses must implement 'from_str' and it must have a type-hinted return value like this:

    class ListOfStringsOption(CCIOptionType):
        @classmethod
        def from_str(cls, v) -> List[str]:
            return [s.strip() for s in v.split(",")]
    """

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
        target_type = signature(cls.from_str).return_annotation

        Dummy = create_model(cls.name or cls.__name__, __root__=(target_type, ...))

        return Dummy.parse_obj(v).__root__


class ListOfStringsOption(CCIOptionType):
    """Parses a list of strings from a comma-delimited string"""

    @classmethod
    def from_str(cls, v) -> List[str]:
        return [s.strip() for s in v.split(",")]


class MappingOption(CCIOptionType):
    """Parses a Mapping of Str->Any from a string in format a:b,c:d"""

    @classmethod
    def from_str(cls, v) -> Dict[str, Any]:
        return parse_list_of_pairs_dict_arg(v)


def parse_list_of_pairs_dict_arg(arg):
    """Process an arg in the format "aa:bb,cc:dd" """
    if isinstance(arg, dict):
        return arg
    elif isinstance(arg, str):
        rc = {}
        for key_value in arg.split(","):
            subparts = key_value.split(":", maxsplit=1)
            if len(subparts) == 2:
                key, value = subparts
                if key in rc:
                    raise TypeError(f"Var specified twice: {key}")
                rc[key] = value
            else:
                raise TypeError(f"Var is not a name/value pair: {key_value}")
        return rc
    else:
        raise TypeError(f"Arg is not a dict or string ({type(arg)}): {arg}")


__all__ = [
    "Field",
    "FilePath",
    "DirectoryPath",
    "parse_list_of_pairs_dict_arg",
    "CCIOptions",
    "CCIOptionType",
    "ListOfStringsOption",
    "MappingOption",
]
