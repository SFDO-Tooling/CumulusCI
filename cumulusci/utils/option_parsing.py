from typing import List, Dict, Any
import json
from inspect import signature

from pydantic import Field, create_model, FilePath, DirectoryPath

from cumulusci.utils.yaml.model_parser import CCIDictModel
from cumulusci.core.utils import process_list_of_pairs_dict_arg
from cumulusci.core.exceptions import TaskOptionsError


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
    "Base class for all options in tasks"

    @classmethod
    def as_task_options(cls):
        return {
            fieldname: _describe_field(field)
            for fieldname, field in cls.__fields__.items()
        }


class CCIOptionType:
    """Base class custom option types.

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
        try:
            return process_list_of_pairs_dict_arg(v)
        except TaskOptionsError as e:
            raise TypeError(e)


# These are so that others don't
# need to import directly from Pydantic
# TODO: Discuss with @davisagli
Field = Field
FilePath = FilePath
DirectoryPath = DirectoryPath
