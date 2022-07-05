import re
import typing as T
from pathlib import Path

from pydantic import Field, root_validator, validator

from cumulusci.tasks.bulkdata.step import DataApi
from cumulusci.utils.yaml.model_parser import CCIDictModel, HashableBaseModel

object_decl = re.compile(r"objects\((\w+)\)", re.IGNORECASE)
field_decl = re.compile(r"fields\((\w+)\)", re.IGNORECASE)


class ExtractDeclaration(HashableBaseModel):
    where: str = None
    fields_: T.Union[list[str], str] = Field(["FIELDS(ALL)"], alias="fields")
    api: DataApi = DataApi.SMART
    sf_object: str = None  # injected, not implied

    @staticmethod
    def parse_field_complex_type(fieldspec):
        """If it's something like FIELDS(...), parse it out"""
        if match := field_decl.match(fieldspec):
            return match.groups()[0].lower()
        else:
            return None

    def sf_object_fits_pattern(self):
        if self.group_type:
            assert self.group_type in (
                "populated",
                "custom",
                "standard",
            ), f"Expected OBJECTS(POPULATED), OBJECTS(CUSTOM) or OBJECTS(STANDARD), not `{self.group_type.upper()}`"
        else:
            assert self.sf_object.isidentifier(), (
                "Value should start with OBJECTS( or be a simple alphanumeric field name"
                f" (underscores allowed) not {self.sf_object}"
            )
        return self.sf_object

    @root_validator
    @classmethod
    def check_where_against_complex(cls, values):
        """Check that a where clause was not used with a group declaration."""
        assert not (
            values.get("where") and "(" in values["sf_object"]
        ), "Cannot specify a `where` clause on a declaration for multiple kinds of objects."
        return values

    @validator("fields_")
    def normalize_fields(cls, vals):
        if isinstance(vals, str):
            vals = [vals]
        for val in vals:
            cls.validate_field(val)
        return vals

    @classmethod
    def validate_field(cls, val):
        assert cls.parse_field_complex_type(val) or val.isidentifier(), val
        if group_type := cls.parse_field_complex_type(val):
            assert group_type in ("custom", "required", "all", "standard"), group_type

        return val


class SimpleExtractDeclaration(ExtractDeclaration):
    # lookups: dict[str, str] = None  # is this used???

    @validator("sf_object")
    def sf_object_fits_pattern(cls, val):
        assert val.isidentifier(), "Not an SObject name"
        return val


class GroupExtractDeclaration(ExtractDeclaration):
    @validator("sf_object")
    def is_group(cls, val):
        assert val._parse_group_type(), "Not a Group"
        return val

    @property
    def group_type(self):
        """If it's something like OBJECT(...), parse it out"""
        return self._parse_group_type(self.sf_object)

    @staticmethod
    def _parse_group_type(val):
        if "(" in val:
            return object_decl.match(val)[1].lower()
        else:
            return None


class ExtractRulesFile(CCIDictModel):
    version: int = 1
    extract: dict[str, T.Union[GroupExtractDeclaration, SimpleExtractDeclaration]]

    @validator("extract")
    def sf_object_fits_pattern(cls, val):
        for name, decl in val.items():
            decl.sf_object = name
            decl.sf_object_fits_pattern()
        return val

    @classmethod
    def parse_extract(cls, source: T.Union[str, Path, T.IO]):
        """Return the extract key after parsing an extract file."""
        return super().parse_from_yaml(source).extract
