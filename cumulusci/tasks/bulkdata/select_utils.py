import random
import re
import typing as T

import numpy as np
import pandas as pd
from annoy import AnnoyIndex
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.preprocessing import StandardScaler

from cumulusci.core.enums import StrEnum
from cumulusci.tasks.bulkdata.extract_dataset_utils.hardcoded_default_declarations import (
    DEFAULT_DECLARATIONS,
)


class SelectStrategy(StrEnum):
    """Enum defining the different selection strategies requested."""

    STANDARD = "standard"
    SIMILARITY = "similarity"
    RANDOM = "random"


class SelectRecordRetrievalMode(StrEnum):
    """Enum defining whether you need all records or match the
    number of records of the local sql file"""

    ALL = "all"
    MATCH = "match"


class SelectOperationExecutor:
    def __init__(self, strategy: SelectStrategy):
        self.strategy = strategy
        self.retrieval_mode = (
            SelectRecordRetrievalMode.ALL
            if strategy == SelectStrategy.SIMILARITY
            else SelectRecordRetrievalMode.MATCH
        )

    def select_generate_query(
        self,
        sobject: str,
        fields: T.List[str],
        user_filter: str,
        limit: T.Union[int, None],
        offset: T.Union[int, None],
    ):
        # For STANDARD strategy
        if self.strategy == SelectStrategy.STANDARD:
            return standard_generate_query(
                sobject=sobject, user_filter=user_filter, limit=limit, offset=offset
            )
        # For SIMILARITY strategy
        elif self.strategy == SelectStrategy.SIMILARITY:
            return similarity_generate_query(
                sobject=sobject,
                fields=fields,
                user_filter=user_filter,
                limit=limit,
                offset=offset,
            )
        # For RANDOM strategy
        elif self.strategy == SelectStrategy.RANDOM:
            return standard_generate_query(
                sobject=sobject, user_filter=user_filter, limit=limit, offset=offset
            )

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
    sobject: str,
    user_filter: str,
    limit: T.Union[int, None],
    offset: T.Union[int, None],
) -> T.Tuple[str, T.List[str]]:
    """Generates the SOQL query for the standard (as well as random) selection strategy"""

    query = f"SELECT Id FROM {sobject}"
    # If user specifies user_filter
    if user_filter:
        query += add_limit_offset_to_user_filter(
            filter_clause=user_filter, limit_clause=limit, offset_clause=offset
        )
    else:
        # Get the WHERE clause from DEFAULT_DECLARATIONS if available
        declaration = DEFAULT_DECLARATIONS.get(sobject)
        if declaration:
            query += f" WHERE {declaration.where}"
        query += f" LIMIT {limit}" if limit else ""
        query += f" OFFSET {offset}" if offset else ""
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
    user_filter: str,
    limit: T.Union[int, None],
    offset: T.Union[int, None],
) -> T.Tuple[str, T.List[str]]:
    """Generates the SOQL query for the similarity selection strategy, with support for TYPEOF on polymorphic fields."""

    # Pre-process the new fields format to create a nested dict structure for TYPEOF clauses
    nested_fields = {}
    regular_fields = []

    for field in fields:
        components = field.split(".")
        if len(components) >= 3:
            # Handle polymorphic fields (format: {relationship_name}.{ref_obj}.{ref_field})
            relationship, ref_obj, ref_field = (
                components[0],
                components[1],
                components[2],
            )
            if relationship not in nested_fields:
                nested_fields[relationship] = {}
            if ref_obj not in nested_fields[relationship]:
                nested_fields[relationship][ref_obj] = []
            nested_fields[relationship][ref_obj].append(ref_field)
        else:
            # Handle regular fields (format: {field})
            regular_fields.append(field)

    # Construct the query fields
    query_fields = []

    # Build TYPEOF clauses for polymorphic fields
    for relationship, references in nested_fields.items():
        type_clauses = []
        for ref_obj, ref_fields in references.items():
            fields_clause = ", ".join(ref_fields)
            type_clauses.append(f"WHEN {ref_obj} THEN {fields_clause}")
        type_clause = f"TYPEOF {relationship} {' '.join(type_clauses)} END"
        query_fields.append(type_clause)

    # Add regular fields to the query
    query_fields.extend(regular_fields)

    # Ensure "Id" is included in the fields list for identification
    if "Id" not in query_fields:
        query_fields.insert(0, "Id")

    # Build the main SOQL query
    fields_to_query = ", ".join(query_fields)
    query = f"SELECT {fields_to_query} FROM {sobject}"

    # Add the user-defined filter clause or default clause
    if user_filter:
        query += add_limit_offset_to_user_filter(
            filter_clause=user_filter, limit_clause=limit, offset_clause=offset
        )
    else:
        # Get the WHERE clause from DEFAULT_DECLARATIONS if available
        declaration = DEFAULT_DECLARATIONS.get(sobject)
        if declaration:
            query += f" WHERE {declaration.where}"
        query += f" LIMIT {limit}" if limit else ""
        query += f" OFFSET {offset}" if offset else ""

    # Return the original input fields with "Id" added if needed
    if "Id" not in fields:
        fields.insert(0, "Id")

    return query, fields  # Return the original input fields with "Id"


def similarity_post_process(
    load_records, query_records: list, sobject: str
) -> T.Tuple[T.List[dict], T.Union[str, None]]:
    """Processes the query results for the similarity selection strategy"""
    # Handle case where query returns 0 records
    if not query_records:
        error_message = f"No records found for {sobject} in the target org."
        return [], error_message

    load_records = list(load_records)
    load_record_count, query_record_count = len(load_records), len(query_records)

    complexity_constant = load_record_count * query_record_count

    closest_records = []

    if complexity_constant < 1000:
        closest_records = annoy_post_process(load_records, query_records)
    else:
        closest_records = levenshtein_post_process(load_records, query_records)

    return closest_records


def annoy_post_process(
    load_records: list, query_records: list
) -> T.Tuple[T.List[dict], T.Union[str, None]]:
    """Processes the query results for the similarity selection strategy using Annoy algorithm for large number of records"""

    query_records = replace_empty_strings_with_missing(query_records)
    load_records = replace_empty_strings_with_missing(load_records)

    hash_features = 100
    num_trees = 10

    query_record_ids = [record[0] for record in query_records]
    query_record_data = [record[1:] for record in query_records]

    record_to_id_map = {
        tuple(query_record_data[i]): query_record_ids[i]
        for i in range(len(query_records))
    }

    final_load_vectors, final_query_vectors = vectorize_records(
        load_records, query_record_data, hash_features=hash_features
    )

    # Create Annoy index for nearest neighbor search
    vector_dimension = final_query_vectors.shape[1]
    annoy_index = AnnoyIndex(vector_dimension, "euclidean")

    for i in range(len(final_query_vectors)):
        annoy_index.add_item(i, final_query_vectors[i])

    # Build the index
    annoy_index.build(num_trees)

    # Find nearest neighbors for each query vector
    n_neighbors = 1

    closest_records = []

    for i, load_vector in enumerate(final_load_vectors):
        # Get nearest neighbors' indices and distances
        nearest_neighbors = annoy_index.get_nns_by_vector(
            load_vector, n_neighbors, include_distances=True
        )
        neighbor_indices = nearest_neighbors[0]  # Indices of nearest neighbors

        for neighbor_index in neighbor_indices:
            # Retrieve the corresponding record from the database
            record = query_record_data[neighbor_index]
            closest_record_id = record_to_id_map[tuple(record)]
            closest_records.append(
                {"id": closest_record_id, "success": True, "created": False}
            )

    return closest_records, None


def levenshtein_post_process(
    load_records: list, query_records: list
) -> T.Tuple[T.List[dict], T.Union[str, None]]:
    """Processes the query results for the similarity selection strategy using Levenshtein algorithm for small number of records"""
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


def add_limit_offset_to_user_filter(
    filter_clause: str,
    limit_clause: T.Union[float, None] = None,
    offset_clause: T.Union[float, None] = None,
) -> str:

    # Extract existing LIMIT and OFFSET from filter_clause if present
    existing_limit_match = re.search(r"LIMIT\s+(\d+)", filter_clause, re.IGNORECASE)
    existing_offset_match = re.search(r"OFFSET\s+(\d+)", filter_clause, re.IGNORECASE)

    if existing_limit_match:
        existing_limit = int(existing_limit_match.group(1))
        if limit_clause is not None:  # Only apply limit_clause if it's provided
            limit_clause = min(existing_limit, limit_clause)
        else:
            limit_clause = existing_limit

    if existing_offset_match:
        existing_offset = int(existing_offset_match.group(1))
        if offset_clause is not None:
            offset_clause = existing_offset + offset_clause
        else:
            offset_clause = existing_offset

    # Remove existing LIMIT and OFFSET from filter_clause, handling potential extra spaces
    filter_clause = re.sub(
        r"\s+OFFSET\s+\d+\s*", " ", filter_clause, flags=re.IGNORECASE
    ).strip()
    filter_clause = re.sub(
        r"\s+LIMIT\s+\d+\s*", " ", filter_clause, flags=re.IGNORECASE
    ).strip()

    if limit_clause is not None:
        filter_clause += f" LIMIT {limit_clause}"
    if offset_clause is not None:
        filter_clause += f" OFFSET {offset_clause}"

    return f" {filter_clause}"


def determine_field_types(df):
    numerical_features = []
    boolean_features = []
    categorical_features = []

    for col in df.columns:
        # Check if the column can be converted to numeric
        try:
            # Attempt to convert to numeric
            df[col] = pd.to_numeric(df[col], errors="raise")
            numerical_features.append(col)
        except ValueError:
            # Check for boolean values
            if df[col].str.lower().isin(["true", "false"]).all():
                # Map to actual boolean values
                df[col] = df[col].str.lower().map({"true": True, "false": False})
                boolean_features.append(col)
            else:
                categorical_features.append(col)

    return numerical_features, boolean_features, categorical_features


def vectorize_records(db_records, query_records, hash_features):
    # Convert database records and query records to DataFrames
    df_db = pd.DataFrame(db_records)
    df_query = pd.DataFrame(query_records)

    # Dynamically determine field types
    numerical_features, boolean_features, categorical_features = determine_field_types(
        df_db
    )

    # Fit StandardScaler on the numerical features of the database records
    scaler = StandardScaler()
    if numerical_features:
        df_db[numerical_features] = scaler.fit_transform(df_db[numerical_features])
        df_query[numerical_features] = scaler.transform(df_query[numerical_features])

    # Use HashingVectorizer to transform the categorical features
    hashing_vectorizer = HashingVectorizer(
        n_features=hash_features, alternate_sign=False
    )

    # For db_records
    hashed_categorical_data_db = []
    for col in categorical_features:
        hashed_db = hashing_vectorizer.fit_transform(df_db[col]).toarray()
        hashed_categorical_data_db.append(hashed_db)

    # For query_records
    hashed_categorical_data_query = []
    for col in categorical_features:
        hashed_query = hashing_vectorizer.transform(df_query[col]).toarray()
        hashed_categorical_data_query.append(hashed_query)

    # Combine all feature types into a single vector for the database records
    db_vectors = []
    if numerical_features:
        db_vectors.append(df_db[numerical_features].values)
    if boolean_features:
        db_vectors.append(
            df_db[boolean_features].astype(int).values
        )  # Convert boolean to int
    if hashed_categorical_data_db:
        db_vectors.append(np.hstack(hashed_categorical_data_db))

    # Concatenate database vectors
    final_db_vectors = np.hstack(db_vectors)

    # Combine all feature types into a single vector for the query records
    query_vectors = []
    if numerical_features:
        query_vectors.append(df_query[numerical_features].values)
    if boolean_features:
        query_vectors.append(
            df_query[boolean_features].astype(int).values
        )  # Convert boolean to int
    if hashed_categorical_data_query:
        query_vectors.append(np.hstack(hashed_categorical_data_query))

    # Concatenate query vectors
    final_query_vectors = np.hstack(query_vectors)

    return final_db_vectors, final_query_vectors


def replace_empty_strings_with_missing(records):
    return [
        [(field if field != "" else "missing") for field in record]
        for record in records
    ]
