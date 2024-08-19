from cumulusci.core.enums import StrEnum
from cumulusci.tasks.bulkdata.extract_dataset_utils.hardcoded_default_declarations import (
    DEFAULT_DECLARATIONS,
)


class SelectStrategy(StrEnum):
    """Enum defining the different selection strategies requested."""

    RANDOM = "random"


def random_generate_query(sobject: str, num_records: float):
    """Generates the SOQL query for the random selection strategy"""
    # Get the WHERE clause from DEFAULT_DECLARATIONS if available
    declaration = DEFAULT_DECLARATIONS.get(sobject)
    if declaration:
        where_clause = declaration.where
    else:
        where_clause = None
    # Construct the query with the WHERE clause (if it exists)
    query = f"SELECT Id FROM {sobject}"
    if where_clause:
        query += f" WHERE {where_clause}"
    query += f" LIMIT {num_records}"

    return query, ["Id"]


def random_post_process(records, num_records: float, sobject: str):
    """Processes the query results for the random selection strategy"""
    try:
        # Handle case where query returns 0 records
        if not records:
            error_message = f"No records found for {sobject} in the target org."
            return [], error_message

        # Add 'success: True' to each record to emulate records have been inserted
        selected_records = [
            {"id": record[0], "success": True, "created": False} for record in records
        ]

        # If fewer records than requested, repeat existing records to match num_records
        if len(selected_records) < num_records:
            original_records = selected_records.copy()
            while len(selected_records) < num_records:
                selected_records.extend(original_records)
            selected_records = selected_records[:num_records]

        return selected_records, None  # Return selected records and None for error

    except Exception as e:
        error_message = f"Error processing query results for {sobject}: {e}"
        return [], error_message
