import collections
import re
import typing as T

from pydantic import validator

from cumulusci.salesforce_api.org_schema import NOT_EXTRACTABLE, Schema
from cumulusci.utils.iterators import partition

from .extract_yml import ExtractDeclaration
from .hardcoded_default_declarations import DEFAULT_DECLARATIONS


def _simplify_sfobject_declarations(declarations, schema: Schema):
    """Generate a new list of declarations such that all sf_object patterns
    (like OBJECTS(CUSTOM)) have been expanded into many declarations
    with specific names and defaults have been merged in."""
    simple_declarations, group_declarations = partition(
        lambda d: d.group_type, declarations
    )
    simple_declarations = list(simple_declarations)
    simple_declarations = _normalize_user_supplied_simple_declarations(
        simple_declarations, DEFAULT_DECLARATIONS
    )
    simple_declarations = _merge_group_declarations_with_simple_declarations(
        simple_declarations, group_declarations, schema
    )
    return simple_declarations


def _merge_group_declarations_with_simple_declarations(
    simple_declarations: T.Iterable[ExtractDeclaration],
    group_declarations: T.Iterable[ExtractDeclaration],
    schema: Schema,
) -> list[ExtractDeclaration]:
    """Expand group declarations to simple declarations and merge
    with existing simple declarations"""
    simple_declarations = list(simple_declarations)
    group_declarations = list(group_declarations)

    specific_sobject_decl_names = [obj.sf_object for obj in simple_declarations]

    simplified_declarations = [
        _expand_group_sobject_declaration(decl, schema) for decl in group_declarations
    ]
    for decl_set in simplified_declarations:
        for decl in decl_set:
            if decl.sf_object not in specific_sobject_decl_names and not any(
                re.match(pat, decl.sf_object, re.IGNORECASE) for pat in NOT_EXTRACTABLE
            ):
                simple_declarations.append(decl)

    return simple_declarations


def _expand_group_sobject_declaration(decl: ExtractDeclaration, schema: Schema):
    """Expand a group sobject declaration to a list of simple declarations"""
    if decl.group_type == "standard":

        def matches_obj(obj):
            return not obj.custom

    elif decl.group_type == "custom":

        def matches_obj(obj):
            return obj.custom

    elif decl.group_type == "all":

        def matches_obj(obj):
            return True

    elif decl.group_type == "populated":

        def matches_obj(obj):
            return obj.count > 1

    else:
        assert 0, decl.group_type

    matching_objects = [obj["name"] for obj in schema.sobjects if matches_obj(obj)]
    decls = [
        synthesize_declaration_for_sobject(obj, decl.fields) for obj in matching_objects
    ]
    return decls


class SimplifiedExtractDeclaration(ExtractDeclaration):
    # a model where sf_object references a single sf_object
    # and every field is a single field name, not FIELDS(OLD)

    # lookups: dict[str, str] = None  # was this used???

    @validator("sf_object")
    def sf_object_fits_pattern(cls, val):
        assert val.isidentifier()
        return val


def _expand_field_definitions(
    sobject_decl: ExtractDeclaration, schema_fields
) -> SimplifiedExtractDeclaration:
    simple_declarations, group_declarations = partition(
        lambda d: "(" in d, sobject_decl.fields
    )
    declarations = list(simple_declarations)
    for c in group_declarations:
        ctype = ExtractDeclaration.parse_field_complex_type(c)
        if not ctype:
            raise TypeError(f"Could not parse {c}")  # FIX THIS EXCEPTION

        if ctype == "standard":
            # find updateable standard fields
            declarations.extend(
                field.name
                for field in schema_fields.values()
                if field.createable and not field.custom
            )
        elif ctype == "custom":
            declarations.extend(
                field.name
                for field in schema_fields.values()
                if field.createable and field.custom
            )
        elif ctype == "required":
            # required fields are always exported
            pass
        elif ctype == "all":
            declarations.extend(
                field.name for field in schema_fields.values() if field.createable
            )
        else:
            raise NotImplementedError(type)
    declarations.extend(
        field.name
        for field in schema_fields.values()
        if (field.createable and not field.nillable and field.name not in declarations)
    )
    new_sobject_decl = dict(sobject_decl)
    del new_sobject_decl["fields_"]
    return SimplifiedExtractDeclaration(**new_sobject_decl, fields=declarations)


def flatten_declarations(
    declarations: T.Iterable[ExtractDeclaration], schema: Schema
) -> list[SimplifiedExtractDeclaration]:
    assert schema.includes_counts, "Schema object was not set up with `includes_counts`"
    merged_declarations = _simplify_sfobject_declarations(declarations, schema)
    simplified_declarations = [
        _expand_field_definitions(decl, schema[decl.sf_object].fields)
        for decl in merged_declarations
    ]

    return simplified_declarations


def synthesize_declaration_for_sobject(sf_object, fields):
    """Fake a declaration for an sobject that was mentioned
    indirectly"""
    return DEFAULT_DECLARATIONS.get(sf_object) or SimplifiedExtractDeclaration(
        sf_object=sf_object, fields=fields
    )


def _normalize_user_supplied_simple_declarations(
    simple_declarations: list[ExtractDeclaration],
    default_declarations: T.Mapping[str, ExtractDeclaration],
) -> list[ExtractDeclaration]:

    duplicates = _find_duplicates(simple_declarations, lambda x: x.sf_object)

    assert not duplicates, f"Duplicate declarations not allowed: {duplicates}"
    simple_declarations = {
        decl.sf_object: _merge_declarations_with_defaults(
            decl, default_declarations.get(decl.sf_object, _DEFAULT_DEFAULTS)
        )
        for decl in simple_declarations
    }
    return list(simple_declarations.values())


def _find_duplicates(input, key):
    counts = collections.Counter((key(v), v) for v in input)
    duplicates = [name for name, count in counts.items() if count > 1]
    return duplicates


def _merge_declarations_with_defaults(
    user_decl: ExtractDeclaration, default_decl: ExtractDeclaration
):
    default_decl = default_decl or _DEFAULT_DEFAULTS
    return ExtractDeclaration(
        sf_object=user_decl.sf_object,
        where=user_decl.where or default_decl.where,
        fields=user_decl.fields or default_decl.fields,
        api=user_decl.api,
    )


_DEFAULT_DEFAULTS = ExtractDeclaration(fields="FIELDS(REQUIRED)")
