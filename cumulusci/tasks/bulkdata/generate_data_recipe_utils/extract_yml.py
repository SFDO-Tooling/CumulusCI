import collections
import re
import typing as T

from pydantic import Field, root_validator, validator

from cumulusci.tasks.bulkdata.step import DataApi
from cumulusci.utils.yaml.model_parser import CCIDictModel, HashableBaseModel

object_decl = re.compile(r"objects\((\w+)\)", re.IGNORECASE)
field_decl = re.compile(r"fields\((\w+)\)", re.IGNORECASE)


class ExtractDeclaration(HashableBaseModel):
    sf_object: str
    where: str = None
    fields_: T.Optional[list[str]] = Field(["FIELDS(ALL)"], alias="fields")
    api: DataApi = DataApi.SMART

    @property
    def complex_type(self):
        if "(" in self.sf_object:
            return self._extract_complex_type(self.sf_object)
        else:
            return None

    @staticmethod
    def parse_field_complex_type(fieldspec):
        if "(" in fieldspec:
            return field_decl.match(fieldspec).groups()[0].lower()
        else:
            return None

    @staticmethod
    def _extract_complex_type(val: str):
        return object_decl.match(val)[1].lower()

    @validator("sf_object")
    def sf_object_fits_pattern(cls, val):
        if object_decl.match(val):
            complex_type = cls._extract_complex_type(val)
            assert complex_type in (
                "populated",
                "custom",
                "standard",
            ), "Expected OBJECTS(POPULATED), OBJECTS(CUSTOM) or OBJECTS(STANDARD), not {self.complex_type}"
        else:
            assert (
                val.isidentifier()
            ), "Value should start with OBJECTS( or be a simple alphanumeric field name (underscores allowed)"
        return val

    @root_validator
    @classmethod
    def check_where_against_complex(cls, values):
        """Automatically populate the `table` key with `sf_object`, if not present."""
        assert not (
            values.get("where") and "(" in values["sf_object"]
        ), "Cannot specify a `where` clause on a declaration for multiple kinds of objects."
        return values

    @classmethod
    def normalize_user_supplied_simple_declarations(
        cls,
        simple_declarations: list["ExtractDeclaration"],
        default_declarations: list["ExtractDeclaration"],
    ) -> list["ExtractDeclaration"]:

        duplicates = find_duplicates(simple_declarations, lambda x: x.sf_object)

        assert not duplicates, f"Duplicate declarations not allowed: {duplicates}"
        simple_declarations = {
            decl.sf_object: merge_declarations_with_defaults(
                decl, default_declarations.get(decl.sf_object)
            )
            for decl in simple_declarations
        }
        simple_declarations = {
            **simple_declarations,
        }
        return list(simple_declarations.values())


class SimplifiedExtractDeclaration(ExtractDeclaration):
    lookups: dict[str, str] = None

    @validator("sf_object")
    def sf_object_fits_pattern(cls, val):
        assert val.isidentifier()
        return val

    @validator("fields_", each_item=True)
    def fields_fit_simplified_pattern(cls, val):
        assert val.isidentifier()
        return val


class ExtractRulesFile(CCIDictModel):
    __root__: list[ExtractDeclaration]


def find_duplicates(input, key):
    counts = collections.Counter((key(v), v) for v in input)
    duplicates = [name for name, count in counts.items() if count > 1]
    return duplicates


DEFAULT_DEFAULTS = ExtractDeclaration(
    sf_object="default_xyzzy", where=None, fields=None
)


def merge_declarations_with_defaults(
    user_decl: ExtractDeclaration, default_decl: ExtractDeclaration
):
    default_decl = default_decl or DEFAULT_DEFAULTS
    return ExtractDeclaration(
        sf_object=user_decl.sf_object,
        where=user_decl.where or default_decl.where,
        fields=user_decl.fields or default_decl.fields,
        api=user_decl.api,
    )
