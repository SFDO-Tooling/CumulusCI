import random
import typing as T

from cumulusci.core.enums import StrEnum
from cumulusci.tasks.bulkdata.extract_dataset_utils.hardcoded_default_declarations import (
    DEFAULT_DECLARATIONS,
)


class SelectStrategy(StrEnum):
    """Enum defining the different selection strategies requested."""

    STANDARD = "standard"
    SIMILARITY = "similarity"
    RANDOM = "random"


class SelectOperationExecutor:
    def __init__(self, strategy: SelectStrategy):
        self.strategy = strategy

    def select_generate_query(
        self, sobject: str, fields: T.List[str], num_records: int
    ):
        # For STANDARD strategy
        if self.strategy == SelectStrategy.STANDARD:
            return standard_generate_query(sobject=sobject, num_records=num_records)
        # For SIMILARITY strategy
        elif self.strategy == SelectStrategy.SIMILARITY:
            return similarity_generate_query(sobject=sobject, fields=fields)
        # For RANDOM strategy
        elif self.strategy == SelectStrategy.RANDOM:
            return standard_generate_query(sobject=sobject, num_records=num_records)

    def select_post_process(
        self, load_records, query_records: list, num_records: int, sobject: str
    ):
        # For STANDARD strategy
        if self.strategy == SelectStrategy.STANDARD:
            return standard_post_process(
                query_records=query_records, num_records=num_records, sobject=sobject
            )
        # For SIMILARITY strategy
        elif self.strategy == SelectStrategy.SIMILARITY:
            return similarity_post_process(
                load_records=load_records, query_records=query_records, sobject=sobject
            )
        # For RANDOM strategy
        elif self.strategy == SelectStrategy.RANDOM:
            return random_post_process(
                query_records=query_records, num_records=num_records, sobject=sobject
            )


def standard_generate_query(
    sobject: str, num_records: int
) -> T.Tuple[str, T.List[str]]:
    """Generates the SOQL query for the standard (as well as random) selection strategy"""
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


def standard_post_process(
    query_records: list, num_records: int, sobject: str
) -> T.Tuple[T.List[dict], T.Union[str, None]]:
    """Processes the query results for the standard selection strategy"""
    # Handle case where query returns 0 records
    if not query_records:
        error_message = f"No records found for {sobject} in the target org."
        return [], error_message

    # Add 'success: True' to each record to emulate records have been inserted
    selected_records = [
        {"id": record[0], "success": True, "created": False} for record in query_records
    ]

    # If fewer records than requested, repeat existing records to match num_records
    if len(selected_records) < num_records:
        original_records = selected_records.copy()
        while len(selected_records) < num_records:
            selected_records.extend(original_records)
        selected_records = selected_records[:num_records]

    return selected_records, None  # Return selected records and None for error


def similarity_generate_query(
    sobject: str,
    fields: T.List[str],
) -> T.Tuple[str, T.List[str]]:
    """Generates the SOQL query for the similarity selection strategy"""
    # Get the WHERE clause from DEFAULT_DECLARATIONS if available
    declaration = DEFAULT_DECLARATIONS.get(sobject)
    if declaration:
        where_clause = declaration.where
    else:
        where_clause = None
    # Construct the query with the WHERE clause (if it exists)

    fields.insert(0, "Id")
    fields_to_query = ", ".join(field for field in fields if field)

    query = f"SELECT {fields_to_query} FROM {sobject}"
    if where_clause:
        query += f" WHERE {where_clause}"

    return query, fields


def similarity_post_process(
    load_records: list, query_records: list, sobject: str
) -> T.Tuple[T.List[dict], T.Union[str, None]]:
    """Processes the query results for the similarity selection strategy"""
    # Handle case where query returns 0 records
    if not query_records:
        error_message = f"No records found for {sobject} in the target org."
        return [], error_message

    closest_records = []

    for record in load_records:
        closest_record = find_closest_record(record, query_records)
        closest_records.append(
            {"id": closest_record[0], "success": True, "created": False}
        )

    return closest_records, None


def random_post_process(
    query_records: list, num_records: int, sobject: str
) -> T.Tuple[T.List[dict], T.Union[str, None]]:
    """Processes the query results for the random selection strategy"""

    if not query_records:
        error_message = f"No records found for {sobject} in the target org."
        return [], error_message

    selected_records = []
    for _ in range(num_records):  # Loop 'num_records' times
        # Randomly select one record from query_records
        random_record = random.choice(query_records)
        selected_records.append(
            {"id": random_record[0], "success": True, "created": False}
        )

    return selected_records, None


def find_closest_record(load_record: list, query_records: list):
    closest_distance = float("inf")
    closest_record = query_records[0]

    for record in query_records:
        distance = calculate_levenshtein_distance(load_record, record[1:])
        if distance < closest_distance:
            closest_distance = distance
            closest_record = record

    return closest_record


def levenshtein_distance(str1: str, str2: str):
    """Calculate the Levenshtein distance between two strings"""
    len_str1 = len(str1) + 1
    len_str2 = len(str2) + 1

    dp = [[0 for _ in range(len_str2)] for _ in range(len_str1)]

    for i in range(len_str1):
        dp[i][0] = i
    for j in range(len_str2):
        dp[0][j] = j

    for i in range(1, len_str1):
        for j in range(1, len_str2):
            cost = 0 if str1[i - 1] == str2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,  # Deletion
                dp[i][j - 1] + 1,  # Insertion
                dp[i - 1][j - 1] + cost,
            )  # Substitution

    return dp[-1][-1]


def calculate_levenshtein_distance(record1: list, record2: list):
    if len(record1) != len(record2):
        raise ValueError("Records must have the same number of fields.")

    total_distance = 0
    total_fields = 0

    for field1, field2 in zip(record1, record2):

        field1 = field1.lower()
        field2 = field2.lower()

        if len(field1) == 0 and len(field2) == 0:
            # If both fields are blank, distance is 0
            distance = 0
        else:
            distance = levenshtein_distance(field1, field2)
            if len(field1) == 0 or len(field2) == 0:
                # If one field is blank, reduce the impact of the distance
                distance = distance * 0.05  # Fixed value for blank vs non-blank

        total_distance += distance
        total_fields += 1

    return total_distance / total_fields if total_fields > 0 else 0
