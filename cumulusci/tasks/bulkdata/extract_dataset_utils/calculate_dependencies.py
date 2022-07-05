import typing as T

from cumulusci.salesforce_api.org_schema import Schema

from .synthesize_extract_declarations import (
    SimplifiedExtractDeclaration,
    synthesize_declaration_for_sobject,
)


class Dependency(T.NamedTuple):
    table_name_from: str
    table_name_to: str
    field_name: str


# FIXME: Merge these methods


def calculate_hard_dependencies(
    decls: list[SimplifiedExtractDeclaration], schema: Schema
) -> dict:
    dependencies = {}
    for source_sfobject, source_decl in decls.items():
        for field_name in source_decl.fields:
            field_info = schema[source_sfobject].fields[field_name]
            references = field_info.referenceTo
            if len(references) == 1:
                target = references[0]
                if not field_info.nillable:  # diff
                    dependencies.setdefault(source_sfobject, []).append(
                        Dependency(source_sfobject, target, field_name)
                    )

    return dependencies


def calculate_dependencies(
    decls: list[SimplifiedExtractDeclaration], schema: Schema
) -> dict:
    dependencies = {}
    for source_sfobject, source_decl in decls.items():
        for field_name in source_decl.fields:
            field_info = schema[source_sfobject].fields[field_name]
            references = field_info.referenceTo
            if len(references) == 1:
                target = references[0]
                dependencies.setdefault(source_sfobject, []).append(
                    Dependency(source_sfobject, target, field_name)
                )

    return dependencies


def extend_declarations_to_include_referenced_tables(
    decls: dict[str, SimplifiedExtractDeclaration], schema: Schema
) -> dict[str, SimplifiedExtractDeclaration]:
    dependencies = calculate_dependencies(decls, schema)
    to_process = list(decls.values())

    while to_process:
        sf_object = to_process.pop()
        my_dependencies = dependencies.get(sf_object)
        if my_dependencies:
            for dep in my_dependencies:
                target_table = dep.to
                if target_table not in decls:
                    required_fields = [
                        field
                        for field in schema[target_table].fields
                        if not field.nillable
                    ]
                    decls[target_table] = synthesize_declaration_for_sobject(
                        sf_object, required_fields
                    )
                    to_process.append(decls[target_table])
