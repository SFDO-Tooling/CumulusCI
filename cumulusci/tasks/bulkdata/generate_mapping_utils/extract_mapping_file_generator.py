import typing as T

from cumulusci.salesforce_api.org_schema import Schema
from cumulusci.tasks.bulkdata.generate_mapping_utils.generate_mapping_from_declarations import (
    SimplifiedExtractDeclarationWithLookups,
    classify_and_filter_lookups,
)

from ..extract_dataset_utils.synthesize_extract_declarations import (
    ExtractDeclaration,
    flatten_declarations,
)


def _mapping_decl_for_extract_decl(
    decl: SimplifiedExtractDeclarationWithLookups,
):
    """Make a CCI extract mapping step from a SimplifiedExtractDeclarationWithLookups"""
    lookups = {lookup: {"table": table} for lookup, table in decl.lookups.items()}
    mapping_dict = {
        "sf_object": decl.sf_object,
    }
    if decl.where:
        mapping_dict["soql_filter"] = decl.where
    mapping_dict["fields"] = decl.fields
    if lookups:
        mapping_dict["lookups"] = lookups

    return (f"Extract {decl.sf_object}", mapping_dict)


def create_extract_mapping_file_from_declarations(
    decls: T.List[ExtractDeclaration], schema: Schema
):
    """Create a mapping file sufficient for driving an extract process
    from an extract declarations file."""
    assert decls is not None
    simplified_decls = flatten_declarations(decls, schema)
    simplified_decls = classify_and_filter_lookups(simplified_decls, schema)
    mappings = [_mapping_decl_for_extract_decl(decl) for decl in simplified_decls]
    return dict(pair for pair in mappings if pair)
