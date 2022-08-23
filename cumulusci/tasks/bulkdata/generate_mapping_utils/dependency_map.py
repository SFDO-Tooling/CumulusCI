import typing as T
from collections import defaultdict

from cumulusci.tasks.bulkdata.extract_dataset_utils.calculate_dependencies import (
    SObjDependency,
)
from cumulusci.utils.collections import OrderedSet, OrderedSetType

StrDependencyMapping = T.Mapping[str, OrderedSetType[SObjDependency]]
SObjectRuleDeclaration = (
    "snowfakery.cci_mapping_files.declaration_parser.SObjectRuleDeclaration"
)


class DependencyMap:
    """Index which tables depend on which other ones (through lookups)

    To make lookups easy later.
    """

    # a dictionary allowing easy lookup of inferred/soft dependencies by parent table
    soft_dependencies: StrDependencyMapping

    # a dictionary allowing lookups by (tablename, fieldname) pairs
    reference_fields: StrDependencyMapping

    _sorted_tables = None  # cache for sorted table computation

    def __init__(
        self,
        table_names: T.Iterable[str],
        dependencies: T.Iterable[SObjDependency],
    ):
        self.dependencies = defaultdict(OrderedSet)
        self.reference_fields = {}
        self._map_references(dependencies)
        self.table_names = tuple(table_names)

    def _map_references(
        self,
        intertable_dependencies: T.Iterable[SObjDependency],
    ):
        for dep in intertable_dependencies:
            table_deps = self.dependencies[dep.table_name_from]
            table_deps.add(dep)
            self.reference_fields[
                (dep.table_name_from, dep.field_name)
            ] = dep.table_name_to

    def target_table_for(self, tablename: str, fieldname: str) -> T.Optional[str]:
        return self.reference_fields.get((tablename, fieldname))

    def get_dependency_order(self):
        """Sort the dependencies to output tables in the right order."""
        if not self._sorted_tables:
            # SnowfakeryPersonAccounts: Add this back in when Snowfakery is integrated with this code.
            # _remove_person_contact_id(self.dependencies)
            self._sorted_tables = _sort_by_dependencies(
                tuple(self.table_names), self.dependencies
            )
        return self._sorted_tables


def _sort_by_dependencies(
    table_names: T.Sequence[str],
    dependencies: T.Mapping[str, OrderedSet],
    priority: int = 0,
):
    "Sort tables by dependency relationships."
    sorted_tables = []
    dependencies = dict(dependencies)

    while table_names:
        remaining = len(table_names)
        leaf_tables = [
            table
            for table in table_names
            if _table_is_free(table, dependencies, sorted_tables, priority)
        ]
        sorted_tables.extend(leaf_tables)
        table_names = [table for table in table_names if table not in sorted_tables]

        # Nothing changed, so we need to attempt other techniques.
        if len(table_names) == remaining:
            # this is a bit tricky.
            # run the algorithm with ONLY the declared/hard
            # dependencies and see if it comes to resolution

            higher_priority_sort = _sort_dependencies_higher_priority(
                table_names, dependencies, priority
            )

            if higher_priority_sort:
                sorted_tables.extend(higher_priority_sort)
            else:
                # I'm stuck. Try randomly
                sorted_tables.append(sorted(table_names)[0])

    return sorted_tables


def _sort_dependencies_higher_priority(
    table_names: T.Iterable[str],
    dependencies: T.Mapping[str, OrderedSet],
    priority: int,
):
    """After a priority-ignoring dependency sort has failed, try sorting ONLY
    on that subset of dependencies marked with a higher priority. This function
    is mututally recursive with `_sort_by_dependencies` so it will ratchet
    up the priority potentially multiple times."""
    relevant_dependencies = (
        dep.priority
        for depset in dependencies.values()
        for dep in depset
        if dep.priority > priority
    )
    lowest_priority_dependency = min(relevant_dependencies, default=None)

    if lowest_priority_dependency is not None:
        return _sort_by_dependencies(
            table_names, dependencies, lowest_priority_dependency
        )


def _table_is_free(
    table_name: str,
    dependencies: StrDependencyMapping,
    sorted_tables: T.Sequence[str],
    priority: int,
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
            or dependency.priority < priority
        ):
            tables_this_table_depends_upon.remove(dependency)

    return len(tables_this_table_depends_upon) == 0


# SnowfakeryPersonAccounts: This code will be enabled when Snowfakery
# is integrated with this code.
# def _remove_person_contact_id(dependencies: T.Mapping[str, SObjDependency]):
#     """Don't allow relationships between a personcontact and an account to mess
#     up the load order.

#     Code adapted from Snowfakery
#     """
#     if "Account" in dependencies:
#         dep_to_person_contact = [
#             dep
#             for dep in dependencies["Account"]
#             if dep.table_name_to.lower() == "personcontact"
#         ]
#         for dep in dep_to_person_contact:
#             dependencies["Account"].remove(dep)
