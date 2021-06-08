def append_where_clause(soql, object_config):
    """Function that applies where clause to soql if it is defined in mapping yml file"""

    where_clause = (
        object_config.soql_filter if object_config.soql_filter is not None else None
    )

    if not where_clause:
        return soql
        # Handle situation where WHERE keyword already specified in mapping yml file
    elif where_clause.lower().startswith("where "):
        soql = f"{soql} {where_clause}"
    else:
        soql = f"{soql} WHERE {where_clause}"

    return soql
