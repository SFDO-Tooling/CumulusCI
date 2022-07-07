import typing as T

from cumulusci.salesforce_api.filterable_objects import NOT_EXTRACTABLE
from cumulusci.salesforce_api.org_schema import Schema

from .synthesize_extract_declarations import (
    SimplifiedExtractDeclaration,
    synthesize_declaration_for_sobject,
)


class Dependency(T.NamedTuple):
    table_name_from: str
    table_name_to: str
    field_name: str


def _calculate_dependencies_for_declarations(
    decls: T.Sequence[SimplifiedExtractDeclaration], schema: Schema
) -> dict[str, list[Dependency]]:
    dependencies = {}
    for decl in decls:
        new_dependencies = _calculate_dependencies_for_sobject(
            decl.sf_object, decl.fields, schema, only_required_fields=False
        )
        dependencies.update(new_dependencies)
    return dependencies


def _calculate_dependencies_for_sobject(
    source_sfobject: str, fields: list[str], schema: Schema, only_required_fields: bool
):
    dependencies = {}
    for field_name in fields:
        field_info = schema[source_sfobject].fields[field_name]
        if not field_info.createable:  # pragma: no cover
            continue
        references = field_info.referenceTo
        if len(references) == 1:
            target = references[0]

            target_disallowed = target in NOT_EXTRACTABLE
            field_disallowed = target_disallowed or not field_info.createable
            field_allowed = not (only_required_fields or field_disallowed)
            if field_info.requiredOnCreate or field_allowed:
                dependencies.setdefault(source_sfobject, []).append(
                    Dependency(source_sfobject, target, field_name)
                )

    return dependencies


def extend_declarations_to_include_referenced_tables(
    decl_list: T.Sequence[SimplifiedExtractDeclaration], schema: Schema
) -> T.Sequence[SimplifiedExtractDeclaration]:
    decls = {decl.sf_object: decl for decl in decl_list}
    dependencies = _calculate_dependencies_for_declarations(decl_list, schema)
    to_process = list(decls.keys())

    while to_process:
        sf_object = to_process.pop()
        assert isinstance(sf_object, str)
        my_dependencies = dependencies.get(sf_object, ())
        for dep in my_dependencies:
            target_table = dep.table_name_to
            if target_table not in decls and target_table not in NOT_EXTRACTABLE:
                required_fields = [
                    field.name
                    for field in schema[target_table].fields.values()
                    if field.requiredOnCreate
                ]
                decls[target_table] = synthesize_declaration_for_sobject(
                    target_table, required_fields
                )

                new_dependencies = _calculate_dependencies_for_sobject(
                    target_table,
                    decls[target_table].fields,
                    schema,
                    only_required_fields=True,
                )
                dependencies.update(new_dependencies)
                to_process.append(target_table)

    return list(decls.values())
