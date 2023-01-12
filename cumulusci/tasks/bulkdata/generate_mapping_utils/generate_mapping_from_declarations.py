import typing as T
from itertools import chain

from cumulusci.salesforce_api.org_schema import Schema
from cumulusci.tasks.bulkdata.mapping_parser import MappingStep
from cumulusci.utils.collections import OrderedSet
from cumulusci.utils.iterators import partition

from ..extract_dataset_utils.calculate_dependencies import SObjDependency
from ..extract_dataset_utils.synthesize_extract_declarations import (
    ExtractDeclaration,
    SimplifiedExtractDeclaration,
    flatten_declarations,
)
from .load_mapping_file_generator import generate_load_mapping_file


class SimplifiedExtractDeclarationWithLookups(SimplifiedExtractDeclaration):
    lookups: T.Dict[str, str]


def create_load_mapping_file_from_extract_declarations(
    decls: T.Sequence[ExtractDeclaration],
    schema: Schema,
    opt_in_only: T.Sequence[str] = (),
) -> T.Dict[str, dict]:
    """Create a mapping file from Extract declarations"""
    simplified_decls = flatten_declarations(decls, schema, opt_in_only)  # FIXME
    simplified_decls_w_lookups = classify_and_filter_lookups(simplified_decls, schema)
    intertable_dependencies = _discover_dependendencies(simplified_decls_w_lookups)

    def _mapping_step(decl):
        fields = tuple(chain(decl.fields, decl.lookups.keys()))
        return MappingStep(
            sf_object=decl.sf_object,
            fields=zip(fields, fields),
            # lookups=lookups,      # lookups can be re-created later, for simplicity
        )

    mapping_steps = [_mapping_step(decl) for decl in simplified_decls_w_lookups]

    mappings = generate_load_mapping_file(mapping_steps, intertable_dependencies, None)
    return mappings


def _discover_dependendencies(simplified_decls: T.Sequence):
    """Look at all of the lookups in a set of declarations to determine
    what depends on what"""
    intertable_dependencies = OrderedSet()

    for decl in simplified_decls:
        for fieldname, tablename in decl.lookups.items():
            intertable_dependencies.add(
                SObjDependency(decl.sf_object, tablename, fieldname)
            )
    return intertable_dependencies


def classify_and_filter_lookups(
    decls: T.Sequence[SimplifiedExtractDeclaration], schema: Schema
) -> T.Sequence[SimplifiedExtractDeclarationWithLookups]:
    """Move lookups into their own field, if they reference a table we're including"""
    referenceable_tables = [decl.sf_object for decl in decls]
    return [_add_lookups_to_decl(decl, schema, referenceable_tables) for decl in decls]


def _add_lookups_to_decl(
    decl: SimplifiedExtractDeclaration,
    schema: Schema,
    referenceable_tables: T.Sequence[str],
) -> SimplifiedExtractDeclarationWithLookups:
    """Look at every declaration and check whether any of the fields it refers to
    are actually lookups. If so, synthesize the lookups declarations."""
    sobject_schema_info = schema[decl.sf_object]
    fields, lookups_and_targets = _fields_and_lookups_for_decl(
        decl, sobject_schema_info, referenceable_tables
    )
    new_decl_data = {
        **dict(decl),
        "fields": list(fields),
        "lookups": dict(lookups_and_targets),
    }
    del new_decl_data["fields_"]
    new_decl = SimplifiedExtractDeclarationWithLookups(**new_decl_data)
    return new_decl


def _fields_and_lookups_for_decl(decl, sobject_schema_info, referenceable_tables):
    """Split fields versus lookups for a declaration"""
    simple_fields, lookups = partition(
        lambda field_name: sobject_schema_info.fields[field_name].referenceTo,
        decl.fields,
    )

    def target_table(field_info):
        if len(field_info.referenceTo) == 1:
            target = field_info.referenceTo[0]
        else:  # pragma: no cover  # TODO: Cover
            target = "Polymorphic lookups are not supported"
        return target

    lookups = list(lookups)

    lookups_and_targets = (
        (lookup, target_table(sobject_schema_info.fields[lookup])) for lookup in lookups
    )
    lookups_and_targets = (
        (lookup, table)
        for lookup, table in lookups_and_targets
        if table in referenceable_tables
    )
    return simple_fields, lookups_and_targets
