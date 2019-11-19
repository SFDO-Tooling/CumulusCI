from copy import deepcopy


def mapping_from_factory_templates(tables):
    """Use the outputs of the factory YAML and convert to Mapping.yml format"""
    dependencies = build_dependencies(tables)
    table_order = sort_dependencies(dependencies, tables)
    mappings = mappings_from_sorted_tables(tables, table_order)
    return mappings


def build_dependencies(tables):
    """Figure out which tables depend on which other ones (through foreign keys)"""
    dependencies = {}
    for table_name, table_info in tables.items():
        for field in table_info.fields.values():
            if field.target_table:
                table_deps = dependencies.setdefault(table_name, set())
                table_deps.add(field.target_table)
    return dependencies


def _table_is_free(table, dependencies, sorted_tables):
    """Check if every child of this table is already sorted"""
    tables_this_table_depends_upon = dependencies.get(table, [])
    for dependency in tables_this_table_depends_upon.copy():
        if dependency in sorted_tables:
            tables_this_table_depends_upon.remove(dependency)

    return len(tables_this_table_depends_upon) == 0


def sort_dependencies(dependencies, tables):
    """"Sort the dependencies to output tables in the right order."""
    dependencies = deepcopy(dependencies)
    sorted_tables = []

    while tables:
        remaining = len(tables)
        leaf_tables = {
            table
            for table in tables
            if _table_is_free(table, dependencies, sorted_tables)
        }
        sorted_tables.extend(leaf_tables)
        tables = [table for table in tables if table not in sorted_tables]
        if len(tables) == remaining:
            raise Exception(f"Circular references: {tables}")
    return sorted_tables


def mappings_from_sorted_tables(tables, table_order):
    """Generate mapping.yml data structures. """
    mappings = {}
    for table_name in table_order:
        table = tables[table_name]
        fields = {
            fieldname: fieldname
            for fieldname, fielddef in table.fields.items()
            if not fielddef.target_table
        }
        lookups = {
            fieldname: {"table": fielddef.target_table, "key_field": fieldname}
            for fieldname, fielddef in table.fields.items()
            if fielddef.target_table
        }
        mappings[f"Insert {table_name}"] = {
            "sf_object": table_name,
            "table": table_name,
            "fields": fields,
            "lookups": lookups,
        }

    return mappings
