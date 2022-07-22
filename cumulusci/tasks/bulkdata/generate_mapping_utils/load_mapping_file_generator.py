import typing as T

from snowfakery.cci_mapping_files.declaration_parser import SObjectRuleDeclaration

from cumulusci.tasks.bulkdata.extract_dataset_utils.calculate_dependencies import (
    SObjDependency,
)
from cumulusci.tasks.bulkdata.generate_mapping_utils.dependency_map import DependencyMap
from cumulusci.tasks.bulkdata.generate_mapping_utils.mapping_transforms import (
    merge_matching_steps,
    recategorize_lookups,
    rename_record_type_fields,
    sort_steps,
)
from cumulusci.tasks.bulkdata.mapping_parser import MappingStep
from cumulusci.utils.collections import OrderedSet, OrderedSetType

# from ..extract_dataset_utils.extract_yml import ExtractDeclaration
from .mapping_generator_post_processes import add_after_statements

# Note that the code in this file is used by Snowfakery, so
# changes need to be coordinated.
#
# It is also intended to someday be used by CCI to generate
# Load Mapping Files from Load Declarations.


# Code adapted from Snowfakery
def generate_load_mapping_file(
    mapping_steps: T.Sequence[MappingStep],
    intertable_dependencies: OrderedSetType[SObjDependency],
    declarations: T.List[SObjectRuleDeclaration] = None,
) -> T.Dict[str, dict]:
    """Generate a mapping file in optimal order with forward references etc.

    Input is a set of a tables, dependencies between them and load declarations"""

    declarations = declarations or []
    declared_dependencies = collect_user_specified_dependencies(declarations)
    # tableinfo = group_by_table(output_sets)
    # mapping_steps = mapping_steps_from_output_sets(output_sets)
    table_names = OrderedSet(mapping.sf_object for mapping in mapping_steps)
    depmap = DependencyMap(
        table_names, intertable_dependencies.union(declared_dependencies)
    )

    # Merge similar steps
    mapping_steps = merge_matching_steps(mapping_steps, depmap)

    # Sort steps according to dependencies
    mapping_steps = sort_steps(mapping_steps, depmap)

    # Normalize various forms of record type fields
    mapping_steps = rename_record_type_fields(mapping_steps, depmap)

    # Detect which fields are lookups and properly set them up
    mapping_steps = recategorize_lookups(mapping_steps, depmap)

    # Apply user-specified declarations
    mapping_steps = apply_declarations(mapping_steps, declarations)

    mappings_dict = mappings_as_dicts(mapping_steps, depmap)
    add_after_statements(mappings_dict)
    return mappings_dict

    # note that it is entirely possible for e.g.
    # M=10 input sets to relate to N=3 tables which generate P=7 load steps.
    #
    # This invariiant will always hold
    #
    # N <= P <= M
    #
    # e.g. 10 Outputsets/Templates generating Accounts, Contacts, Opportunities
    # But Accounts have 5 different update keys and the other two have none.


# Code adapted from Snowfakery
# def group_by_table(
#     output_sets: T.Sequence[OutputSet],
# ) -> T.Mapping[str, UnifiedTableInfo]:
#     """In some contexts: Snowfakery in particular, a table may be referredd
#     to many times. This function groups all output sets that refer to
#     a particular table."""
#     tables = {}
#     for output_set in output_sets:
#         if output_set.table_name not in tables:
#             tables[output_set.table_name] = UnifiedTableInfo(
#                 output_set.table_name, [], OrderedSet()
#             )
#         tableinfo = tables[output_set.table_name]
#         tableinfo.output_sets.append(output_set)
#         tableinfo.fields.update(output_set.fields)
#     return tables


# Code adapted from Snowfakery
# def mapping_steps_from_output_sets(
#     output_sets: T.List[OutputSet],
# ) -> T.List[MappingStep]:
#     """Load Steps are roughly the same as mapping file steps"""
#     mapping_steps = []
#     for output_set in output_sets:
#         output_set: OutputSet

#         if output_set.update_key:  # pragma: no cover  # TODO: Cover
#             action = DataOperationType.SMART_UPSERT
#         else:
#             action = DataOperationType.INSERT

#         mapping_steps.append(
#             MappingStep(
#                 action=action,
#                 sf_object=output_set.table_name,
#                 update_key=output_set.update_key,
#                 fields=tuple(output_set.fields),
#             )
#         )

#     return mapping_steps


# Code adapted from Snowfakery
# TODO: Move this Snowfakery-specific code elsewhere
# if tables.get("Account") and tables["Account"].fields.get(
#     "PersonContactId"
# ):  # pragma: no cover  # TODO: Cover
#     del tables["Account"].fields["PersonContactId"]


def collect_user_specified_dependencies(
    declarations: T.Iterable[SObjectRuleDeclaration],
) -> OrderedSetType[SObjDependency]:
    declared_dependencies = [decl for decl in declarations if decl.load_after]
    return OrderedSet(
        [
            SObjDependency(decl.sf_object, decl.load_after, "DECLARED", True)
            for decl in declared_dependencies
        ]
    )


def mappings_as_dicts(
    load_steps: T.List[MappingStep],
    depmap: DependencyMap,
) -> T.Mapping[str, T.Dict]:
    """Generate mapping.yml data structures."""
    mappings = {}
    for mapping_step in load_steps:
        step_name = f"{mapping_step.action.value.title()} {mapping_step.sf_object}"
        if mapping_step.update_key:
            step_name += f" {mapping_step.update_key}"

        assert step_name not in mappings

        # TODO: Figure out where Snowfakery would put all of this code.
        #

        # if load_step.update_key:  # pragma: no cover  # TODO: Cover
        #     assert mapping["action"] == "upsert"
        #     mapping["update_key"] = load_step.update_key
        #     mapping["filters"] = [f"_sf_update_key = '{load_step.update_key}'"]
        #     step_name = f"Upsert {table_name} on {load_step.update_key}"
        # else:
        #     step_name = f"Insert {table_name}"
        #     any_other_step_for_this_table_has_update_key = any(
        #         ls
        #         for ls in load_steps
        #         if (ls.table_name == table_name and ls.update_key)
        #     )
        #     if (
        #         any_other_step_for_this_table_has_update_key
        #     ):  # pragma: no cover  # TODO: Cover
        #         mapping["filters"] = ["_sf_update_key = NULL"]

        mappings[step_name] = mapping_step.dict(
            by_alias=True,
            exclude_defaults=True,
        )
    return mappings


def apply_declarations(
    mapping_steps: T.List[MappingStep],
    declarations: T.List[SObjectRuleDeclaration] = None,
) -> T.List[MappingStep]:
    """Apply user-specified declarations"""

    declarations = {decl.sf_object: decl for decl in declarations}

    def doit(mapping_step: MappingStep) -> MappingStep:
        if sobject_declarations := declarations.get(
            mapping_step.sf_object
        ):  # pragma: no cover  # TODO: Cover
            return MappingStep(
                **{**mapping_step.dict(), **sobject_declarations.as_mapping()}
            )
        else:
            return mapping_step

    return [doit(step) for step in mapping_steps]
