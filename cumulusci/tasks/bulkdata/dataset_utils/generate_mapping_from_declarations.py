from itertools import chain, filterfalse, tee

from simple_salesforce import Salesforce

from cumulusci.salesforce_api.org_schema import Schema
from cumulusci.utils.http.multi_request import CompositeParallelSalesforce

from .cci_mapping_file_generator import OutputSet, generate_mapping
from .extract_yml import ExtractDeclaration, SimplifiedExtractDeclaration
from .synthesize_declarations import (
    SKIP_PATTERNS,
    Dependency,
    extend_declarations_to_include_referenced_tables,
    flatten_declarations,
)


def mapping_decl_for_extract_decl(
    decl: SimplifiedExtractDeclaration,
):

    lookups = {lookup: {"table": table} for lookup, table in decl.lookups.items()}
    mapping_dict = {
        "sf_object": decl.sf_object,
    }
    if decl.where:
        mapping_dict["soql_filter"] = decl.where
    mapping_dict["fields"] = decl.fields
    mapping_dict["lookups"] = lookups

    if mapping_dict.get("fields") or mapping_dict.get("lookups"):
        return (f"Insert {decl.sf_object}", mapping_dict)
    else:
        return None


def create_extract_and_load_mapping_file_from_declarations(
    decls: list[ExtractDeclaration], schema: Schema, sf: Salesforce
) -> dict:
    simplified_decls = simplify_declarations(decls, schema, sf)
    intertable_dependencies = set()
    for decl in simplified_decls.values():
        for fieldname, tablename in decl.lookups.items():
            intertable_dependencies.add(
                Dependency(decl.sf_object, tablename, fieldname)
            )

    output_sets = [
        OutputSet(decl.sf_object, None, tuple(chain(decl.fields, decl.lookups.keys())))
        for decl in simplified_decls.values()
    ]

    mappings = generate_mapping(output_sets, intertable_dependencies, None)
    return mappings


def create_extract_mapping_file_from_declarations(
    decls: list[ExtractDeclaration], schema: Schema, sf: Salesforce
):
    assert decls is not None
    simplified_decls = simplify_declarations(decls, schema, sf).values()
    mappings = [mapping_decl_for_extract_decl(decl) for decl in simplified_decls]
    return dict(pair for pair in mappings if pair)


def simplify_declarations(
    extract_declarations: list[ExtractDeclaration], schema: Schema, sf: Salesforce
):
    potential_objects = [
        obj.name for obj in schema.values() if obj.queryable and obj.createable
    ]
    populated_sobjects = find_populated_objects(sf, potential_objects)
    flattened_declarations = {
        decl.sf_object: decl
        for decl in flatten_declarations(
            extract_declarations, schema, populated_sobjects
        )
    }
    finalized_declarations = {
        objname: flattened_declarations[objname]
        for objname in populated_sobjects
        if (objname in flattened_declarations)
    }
    extend_declarations_to_include_referenced_tables(finalized_declarations, schema)

    classify_and_filter_lookups(finalized_declarations, schema)

    return finalized_declarations


def classify_and_filter_lookups(decls, schema: Schema):
    """Move lookups into their own field, if they reference a table we're including"""
    referenceable_tables = [decl.sf_object for decl in decls.values()]
    for decl in decls.values():
        sobject_schema_info = schema[decl.sf_object]
        fields, lookups_and_targets = fields_and_lookups_for_decl(
            decl, sobject_schema_info, referenceable_tables
        )
        decl.fields = list(fields)
        decl.lookups = dict(lookups_and_targets)


def find_populated_objects(sf, objs):
    with CompositeParallelSalesforce(sf, max_workers=8, chunk_size=5) as cpsf:
        responses, errors = cpsf.do_composite_requests(
            (
                {
                    "method": "GET",
                    "url": f"/services/data/v{sf.sf_version}/query/?q=select count() from {obj}",
                    "referenceId": f"ref{obj}",
                }
                for obj in objs
                if not any(pat.match(obj) for pat in SKIP_PATTERNS)
            )
        )
        from pprint import pprint

        errors = list(errors)
        if errors:
            pprint(("Errors", list(errors)))
        errors, successes = partition(
            lambda response: response["httpStatusCode"] == 200, responses
        )
        errors = list(errors)
        if errors:
            pprint(("Errors", list(errors)))

    successes = list(successes)

    non_empty = (
        response for response in successes if response["body"]["totalSize"] > 0
    )
    non_empty = list(non_empty)

    return [response["referenceId"].removeprefix("ref") for response in non_empty]


def fields_and_lookups_for_decl(decl, sobject_schema_info, referenceable_tables):
    simple_fields, lookups = partition(
        lambda field_name: sobject_schema_info.fields[field_name].referenceTo,
        decl.fields,
    )

    def target_table(field_info):
        if len(field_info.referenceTo) == 1:
            target = field_info.referenceTo[0]
        else:
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


# merge these
def partition(pred, iterable):
    "Use a predicate to partition entries into false entries and true entries"
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = tee(iterable)
    return filterfalse(pred, t1), filter(pred, t2)
