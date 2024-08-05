# pyright: strict

import typing as T
from itertools import chain

from snowfakery.cci_mapping_files.declaration_parser import SObjectRuleDeclaration

from cumulusci.salesforce_api.org_schema import Schema
from cumulusci.tasks.bulkdata.generate_mapping_utils.generate_mapping_from_declarations import (
    _discover_dependendencies,
    classify_and_filter_lookups,
)
from cumulusci.tasks.bulkdata.mapping_parser import MappingStep

from ..extract_dataset_utils.synthesize_extract_declarations import (
    ExtractDeclaration,
    flatten_declarations,
)
from .load_mapping_file_generator import generate_load_mapping_file


def create_extract_mapping_file_from_declarations(
    decls: T.List[ExtractDeclaration],
    schema: Schema,
    opt_in_only: T.Sequence[str],
    loading_rules: T.Sequence[SObjectRuleDeclaration] = (),
):
    """Create a mapping file sufficient for driving an extract process
    from an extract declarations file."""
    assert decls is not None
    simplified_decls = flatten_declarations(decls, schema, opt_in_only)
    simplified_decls_w_lookups = classify_and_filter_lookups(simplified_decls, schema)
    intertable_dependencies = _discover_dependendencies(simplified_decls_w_lookups)

    def _mapping_step(decl):
        fields = tuple(chain(decl.fields, decl.lookups.keys()))
        return MappingStep(
            sf_object=decl.sf_object,
            fields=dict(zip(fields, fields)),
            soql_filter=decl.where if decl.where else None,
            api=decl.api.value if decl.api else None
            # lookups=lookups,      # lookups can be re-created later, for simplicity
        )

    mapping_steps = [_mapping_step(decl) for decl in simplified_decls_w_lookups]

    # To generate mapping file with the correct order
    mappings = generate_load_mapping_file(
        mapping_steps, intertable_dependencies, loading_rules
    )
    return mappings
