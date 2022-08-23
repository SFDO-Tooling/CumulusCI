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

# Note that the code in this file is also used by Snowfakery, so
# changes need to be coordinated.
#
# It is also intended to someday be used by CCI to generate
# Load Mapping Files from Load Declarations.


# Code adapted from Snowfakery
def generate_load_mapping_file(
    mapping_steps: T.Sequence[MappingStep],
    intertable_dependencies: OrderedSetType[SObjDependency],
    load_declarations: T.List[SObjectRuleDeclaration] = None,
) -> T.Dict[str, dict]:
    """Generate a mapping file in optimal order with forward references etc.

    Input is a set of a tables, dependencies between them and load declarations"""

    load_declarations = load_declarations or []
    declared_dependencies = collect_user_specified_dependencies(load_declarations)
    table_names = OrderedSet(mapping.sf_object for mapping in mapping_steps)
    depmap = DependencyMap(
        table_names, intertable_dependencies.union(declared_dependencies)
    )

    # Merge similar steps (output step count will be equal or less)
    mapping_steps = merge_matching_steps(mapping_steps, depmap)

    # Sort steps according to dependencies
    mapping_steps = sort_steps(mapping_steps, depmap)

    # Normalize various forms of record type fields
    mapping_steps = rename_record_type_fields(mapping_steps, depmap)

    # Detect which fields are lookups and properly set them up
    mapping_steps = recategorize_lookups(mapping_steps, depmap)

    # Apply user-specified declarations
    mapping_steps = apply_declarations(mapping_steps, load_declarations)

    mappings_dict = mappings_as_dicts(mapping_steps, depmap)
    add_after_statements(mappings_dict)
    return mappings_dict

    # note that it is entirely possible for e.g.
    # M=10 input mapping steps to relate to N=3 tables which generate P=7 load steps.
    #
    # This invariiant will always hold
    #
    # N <= P <= M
    #
    # e.g. 10 Snowfakery Templates generating Accounts, Contacts, Opportunities
    # But Accounts have 5 different update keys and the other two have none.


def collect_user_specified_dependencies(
    declarations: T.Iterable[SObjectRuleDeclaration],
) -> OrderedSetType[SObjDependency]:
    """The user can specify load order dependencies."""
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
        # Will be used by Snowfakery to generate Upsert mapping files
        if mapping_step.update_key:
            step_name += f" {'_'.join(mapping_step.update_key)}"

        assert step_name not in mappings

        mappings[step_name] = mapping_step.dict(
            by_alias=True,
            exclude_defaults=True,
        )
    return mappings


def apply_declarations(
    mapping_steps: T.List[MappingStep],
    load_declarations: T.List[SObjectRuleDeclaration] = None,
) -> T.List[MappingStep]:
    """Apply user-specified declarations.
    Will be used when this code is used to generate load mappings
    from schemas and SQL instead of from ExtractDeclarations."""

    load_declarations = {decl.sf_object: decl for decl in load_declarations}

    def doit(mapping_step: MappingStep) -> MappingStep:
        if sobject_declarations := load_declarations.get(mapping_step.sf_object):
            return MappingStep(
                **{**mapping_step.dict(), **sobject_declarations.as_mapping()}
            )
        else:
            return mapping_step

    return [doit(step) for step in mapping_steps]
