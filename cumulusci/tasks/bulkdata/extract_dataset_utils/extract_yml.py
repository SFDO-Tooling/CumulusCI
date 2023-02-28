import re
import typing as T
from pathlib import Path

from pydantic import Field, validator

from cumulusci.core.enums import StrEnum
from cumulusci.tasks.bulkdata.step import DataApi
from cumulusci.utils.yaml.model_parser import CCIDictModel, HashableBaseModel

object_decl = re.compile(r"objects\((\w+)\)", re.IGNORECASE)
field_decl = re.compile(r"fields\((\w+)\)", re.IGNORECASE)


class SFObjectGroupTypes(StrEnum):
    all = "all"
    custom = "custom"
    standard = "standard"


class SFFieldGroupTypes(StrEnum):
    all = "all"
    custom = "custom"
    standard = "standard"
    required = "required"


class ExtractDeclaration(HashableBaseModel):
    where: T.Optional[str] = None
    fields_: T.Union[T.List[str], str] = Field(["FIELDS(ALL)"], alias="fields")
    api: DataApi = DataApi.SMART
    sf_object: T.Optional[str] = None  # injected, not declared explicitly

    @staticmethod
    def parse_field_complex_type(fieldspec):
        """If it's something like FIELDS(...), parse it out"""
        if match := field_decl.match(fieldspec):
            matching_group = match.groups()[0].lower()
            field_group_type = getattr(SFFieldGroupTypes, matching_group, None)
            return field_group_type
        else:
            return None

    def assert_sf_object_fits_pattern(self):
        if self.is_group:
            assert (
                self.group_type in SFObjectGroupTypes
            ), f"Expected OBJECTS(ALL), OBJECTS(CUSTOM) or OBJECTS(STANDARD), not `{self.group_type.upper()}`"
        else:
            assert self.sf_object.isidentifier(), (
                "Value should start with OBJECTS( or be a simple alphanumeric field name"
                f" (underscores allowed) not {self.sf_object}"
            )
        return self.sf_object

    def assert_check_where_against_complex(self):
        """Check that a where clause was not used with a group declaration."""
        assert not (
            self.where and self.is_group
        ), "Cannot specify a `where` clause on a declaration for multiple kinds of objects."

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
            assert group_type, (
                "group_type in OBJECT(group_type) should be one of "
                f"{tuple(SFFieldGroupTypes.__members__.keys())}, "
                f"not {val}"
            )

        return val

    @property
    def is_group(self):
        return bool(self.group_type)

    @property
    def group_type(self):
        """If it's something like OBJECT(...), parse it out"""
        val = self._parse_group_type(self.sf_object)
        if val:
            group_type = getattr(SFObjectGroupTypes, val, None)
            assert group_type, (
                "group_type in OBJECT(group_type) should be one of "
                f"{tuple(SFObjectGroupTypes.__members__.keys())}, "
                f"not {val}"
            )
            return group_type

    @staticmethod
    def _parse_group_type(val):
        if "(" in val:
            return object_decl.match(val)[1].lower()
        else:
            return None


class ExtractRulesFile(CCIDictModel):
    version: int = 1
    extract: T.Dict[str, ExtractDeclaration]

    @validator("extract")
    def inject_sf_object_name(cls, val):
        for sf_object, decl in val.items():
            decl.sf_object = sf_object
            decl.assert_sf_object_fits_pattern()
            decl.assert_check_where_against_complex()

        return val

    @classmethod
    def parse_extract(cls, source: T.Union[str, Path, T.IO]):
        """Return the extract key after parsing an extract file."""
        return super().parse_from_yaml(source).extract
