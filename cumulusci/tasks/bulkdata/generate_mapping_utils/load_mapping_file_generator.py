import typing as T
from collections import defaultdict

from snowfakery.salesforce import find_record_type_column

from cumulusci.tasks.bulkdata.extract_dataset_utils.calculate_dependencies import (
    Dependency,
)
from cumulusci.utils.collections import OrderedSet, OrderedSetType

from ..extract_dataset_utils.extract_yml import ExtractDeclaration
from .mapping_generator_post_processes import add_after_statements

# Note that the code in this file is used by Snowfakery, so
# changes need to be coordinated.
#
# It is also intended to someday be used by CCI to generate
# Load Mapping Files from Load Declarations.


class OutputSet(T.NamedTuple):
    # in the Snowfakery context this represents the output of
    # a single template
    # in CCI, a single table or mapping file step

    table_name: str
    update_key: T.Optional[str]
    fields: T.Sequence[str]


class UnifiedTableInfo(T.NamedTuple):
    name: str
    output_sets: T.Sequence[OutputSet]
    fields: OrderedSetType[str]


# Code adapted from Snowfakery
def generate_load_mapping_file(
    output_sets: T.Sequence[OutputSet],
    intertable_dependencies: OrderedSetType[Dependency],
    declarations: T.Mapping[str, ExtractDeclaration] = None,
) -> T.Dict[str, dict]:
    """Generate a mapping file in optimal order with forward references etc.

    Input is a set of a tables, dependencies between them and load declarations"""
    declarations = declarations or {}
    relevant_declarations = [decl for decl in declarations.values() if decl.load_after]
    depmap = DependencyMap(intertable_dependencies, relevant_declarations)

    tableinfo = group_by_table(output_sets)

    remove_person_contact_id(depmap.soft_dependencies, tableinfo)
    table_order = sort_dependencies(
        depmap.soft_dependencies, depmap.hard_dependencies, tuple(tableinfo.keys())
    )

    # note that it is entirely possible for e.g.
    # M=10 OutputSets to relate to N=3 tables which generate P=7 load steps.
    #
    # This invariiant will always hold
    #
    # N <= P <= M
    #
    # e.g. 10 Outputsets/Templates generating Accounts, Contacts, Opportunities
    # But Accounts have 5 different update keys and the other two have none.
    load_steps = load_steps_from_tableinfos(tableinfo, table_order)
    mappings = mappings_from_load_steps(load_steps, depmap, declarations)
    add_after_statements(mappings)
    return mappings


# Code adapted from Snowfakery
def group_by_table(
    output_sets: T.Sequence[OutputSet],
) -> T.Mapping[str, UnifiedTableInfo]:
    """In some contexts: Snowfakery in particular, a table may be referredd
    to many times. This function groups all output sets that refer to
    a particular table."""
    tables = {}
    for output_set in output_sets:
        if output_set.table_name not in tables:
            tables[output_set.table_name] = UnifiedTableInfo(
                output_set.table_name, [], OrderedSet()
            )
        tableinfo = tables[output_set.table_name]
        tableinfo.output_sets.append(output_set)
        tableinfo.fields.update(output_set.fields)
    return tables


class LoadStep(T.NamedTuple):
    action: str
    table_name: str
    update_key: T.Optional[str]
    fields: T.Sequence[str]


# Code adapted from Snowfakery
def load_steps_from_tableinfos(
    tables: T.Dict[str, UnifiedTableInfo], table_order: T.List[str]
) -> T.List[LoadStep]:
    """Load Steps are roughly the same as mapping file steps"""
    load_steps = OrderedSet()
    for table_name, tableinfo in tables.items():
        for output_set in tableinfo.output_sets:

            if output_set.update_key:  # pragma: no cover  # TODO: Cover
                action = "upsert"
            else:
                action = "insert"

            load_steps.add(
                LoadStep(
                    action,
                    table_name,
                    output_set.update_key,
                    tuple(tableinfo.fields.keys()),
                )
            )

    load_steps_as_list = list(load_steps)
    load_steps_as_list.sort(key=lambda step: table_order.index(step.table_name))
    return load_steps_as_list


# Code adapted from Snowfakery
def remove_person_contact_id(
    dependencies: T.Mapping[str, Dependency], tables: T.Mapping[str, UnifiedTableInfo]
):
    """Don't allow relationships between a personcontact and an account to mess
    up the load order.

    Code adapted from Snowfakery
    """
    if "Account" in dependencies:  # pragma: no cover  # TODO: Cover
        dep_to_person_contact = [
            dep
            for dep in dependencies["Account"]
            if dep.table_name_to.lower() == "personcontact"
        ]
        for dep in dep_to_person_contact:
            dependencies["Account"].remove(dep)

    if tables.get("Account") and tables["Account"].fields.get(
        "PersonContactId"
    ):  # pragma: no cover  # TODO: Cover
        del tables["Account"].fields["PersonContactId"]


StrDependencyMapping = T.Mapping[str, OrderedSetType[Dependency]]


# Code adapted from Snowfakery
class DependencyMap:
    """Index which tables depend on which other ones (through lookups)

    To make lookups easy later.
    """

    # a dictionary allowing easy lookup of inferred/soft dependencies by parent table
    soft_dependencies: StrDependencyMapping

    # a dictionary allowing easy lookup of specified/hard dependencies by parent table
    hard_dependencies: StrDependencyMapping

    # a dictionary allowing lookups by (tablename, fieldname) pairs
    reference_fields: StrDependencyMapping

    def __init__(
        self,
        intertable_dependencies: T.Iterable[Dependency],
        declarations: T.Sequence[ExtractDeclaration] = None,
    ):
        self.soft_dependencies = defaultdict(OrderedSet)
        self.hard_dependencies = defaultdict(OrderedSet)
        self.reference_fields = {}
        declarations = declarations or ()
        self._map_dependencies(intertable_dependencies, declarations)

    def _map_dependencies(
        self,
        intertable_dependencies: T.Iterable[Dependency],
        declarations: T.Sequence[ExtractDeclaration] = None,
    ):
        for dep in intertable_dependencies:
            table_deps = self.soft_dependencies[dep.table_name_from]
            table_deps.add(dep)
            self.reference_fields[
                (dep.table_name_from, dep.field_name)
            ] = dep.table_name_to

        for decl in declarations:  # pragma: no cover  # TODO: Cover
            for target in decl.load_after:
                self.hard_dependencies[decl.sf_object].add(
                    Dependency(decl.sf_object, target, "(none)")
                )

    def target_table_for(self, tablename: str, fieldname: str) -> T.Optional[str]:
        return self.reference_fields.get((tablename, fieldname))


# Code adapted from Snowfakery
def _table_is_free(
    table_name: str,
    dependencies: StrDependencyMapping,
    sorted_tables: T.Sequence[str],
):
    """Check if every child of this table is already sorted

    Look at the unit test test_table_is_free_simple to see some
    usage examples.
    """
    tables_this_table_depends_upon = dependencies.get(table_name, OrderedSet()).copy()
    for dependency in sorted(tables_this_table_depends_upon):
        if (
            dependency.table_name_to in sorted_tables
            or dependency.table_name_to == table_name
        ):
            tables_this_table_depends_upon.remove(dependency)

    return len(tables_this_table_depends_upon) == 0


# Code adapted from Snowfakery
def sort_dependencies(
    soft_dependencies: StrDependencyMapping,
    hard_dependencies: StrDependencyMapping,
    tables_names: T.Sequence[str],
):
    """Sort the dependencies to output tables in the right order."""
    dependencies = {**soft_dependencies, **hard_dependencies}
    sorted_tables = []

    while tables_names:
        remaining = len(tables_names)
        leaf_tables = [
            table
            for table in tables_names
            if _table_is_free(table, dependencies, sorted_tables)
        ]
        sorted_tables.extend(leaf_tables)
        tables_names = [table for table in tables_names if table not in sorted_tables]
        if len(tables_names) == remaining:

            # this is a bit tricky.
            # run the algorithm with ONLY the declared/hard
            # dependencies and see if it comes to resolution
            if (
                soft_dependencies and hard_dependencies
            ):  # pragma: no cover  # TODO: Cover
                subset = sort_dependencies({}, hard_dependencies, tables_names.copy())
                sorted_tables.extend(subset)
            else:  # pragma: no cover  # TODO: Cover
                sorted_tables.append(sorted(tables_names)[0])

    return sorted_tables


# Code adapted from Snowfakery
def mappings_from_load_steps(
    load_steps: T.List[LoadStep],
    depmap: DependencyMap,
    declarations: T.Mapping[str, ExtractDeclaration],
):
    """Generate mapping.yml data structures."""
    mappings = {}
    for load_step in load_steps:
        table_name = load_step.table_name
        record_type_col = find_record_type_column(table_name, load_step.fields)

        fields = [
            fieldname
            for fieldname in load_step.fields
            if not depmap.target_table_for(table_name, fieldname)
            and fieldname != record_type_col
        ]
        if record_type_col:  # pragma: no cover  # TODO: Cover
            fields["RecordTypeId"] = record_type_col

        lookups = {
            fieldname: {
                "table": depmap.target_table_for(table_name, fieldname),
                "key_field": fieldname,
            }
            for fieldname in load_step.fields
            if depmap.target_table_for(table_name, fieldname)
        }
        if table_name == "PersonContact":  # pragma: no cover  # TODO: Cover
            sf_object = "Contact"
        else:
            sf_object = table_name
        mapping = {"sf_object": sf_object, "table": table_name, "fields": fields}
        if lookups:
            mapping["lookups"] = lookups

        sobject_declarations = declarations.get(table_name)
        if sobject_declarations:  # pragma: no cover  # TODO: Cover
            mapping.update(sobject_declarations.as_mapping())

        if load_step.update_key:  # pragma: no cover  # TODO: Cover
            mapping["action"] = "upsert"
            mapping["update_key"] = load_step.update_key
            mapping["filters"] = [f"_sf_update_key = '{load_step.update_key}'"]
            step_name = f"Upsert {table_name} on {load_step.update_key}"
        else:
            step_name = f"Insert {table_name}"
            any_other_loadstep_for_this_table_has_update_key = any(
                ls
                for ls in load_steps
                if (ls.table_name == table_name and ls.update_key)
            )
            if (
                any_other_loadstep_for_this_table_has_update_key
            ):  # pragma: no cover  # TODO: Cover
                mapping["filters"] = ["_sf_update_key = NULL"]

        mappings[step_name] = mapping

    return mappings
