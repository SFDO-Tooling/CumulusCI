import logging
import random
import re
import typing as T
from enum import Enum

from pydantic import Field, root_validator, validator

from cumulusci.core.enums import StrEnum
from cumulusci.tasks.bulkdata.utils import CaseInsensitiveDict
from cumulusci.utils import get_cci_upgrade_command
from cumulusci.utils.yaml.model_parser import CCIDictModel

logger = logging.getLogger(__name__)
try:
    import numpy as np
    import pandas as pd
    from annoy import AnnoyIndex
    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.preprocessing import StandardScaler

    OPTIONAL_DEPENDENCIES_AVAILABLE = True
except ImportError:
    logger.warning(
        f"Optional dependencies are missing. "
        "Handling high volumes of records for the 'select' functionality will be significantly slower, "
        "as optimizations for this feature are currently disabled. "
        f"To enable optimized performance, install all required dependencies using: {get_cci_upgrade_command()}[select]\n"
    )
    OPTIONAL_DEPENDENCIES_AVAILABLE = False


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


ENUM_VALUES = {
    v.value.lower(): v.value
    for enum in [SelectStrategy]
    for v in enum.__members__.values()
}


class SelectOptions(CCIDictModel):
    filter: T.Optional[str] = None  # Optional filter for selection
    strategy: SelectStrategy = SelectStrategy.STANDARD  # Strategy for selection
    priority_fields: T.Dict[str, str] = Field({})
    threshold: T.Optional[float] = None

    @validator("strategy", pre=True)
    def validate_strategy(cls, value):
        if isinstance(value, Enum):
            return value

        if value:
            matched_strategy = ENUM_VALUES.get(value.lower())
            if matched_strategy:
                return matched_strategy

        raise ValueError(f"Invalid strategy value: {value}")

    @validator("priority_fields", pre=True)
    def standardize_fields_to_dict(cls, values):
        if values is None:
            values = {}
        if type(values) is list:
            values = {elem: elem for elem in values}
        return CaseInsensitiveDict(values)

    @root_validator
    def validate_threshold_and_strategy(cls, values):
        threshold = values.get("threshold")
        strategy = values.get("strategy")

        if threshold is not None:
            values["threshold"] = float(threshold)  # Convert to float

            if not (0 <= values["threshold"] <= 1):
                raise ValueError(
                    f"Threshold must be between 0 and 1, got {values['threshold']}."
                )

            if strategy != SelectStrategy.SIMILARITY:
                raise ValueError(
                    "If a threshold is specified, the strategy must be set to 'similarity'."
                )

        return values


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
        _, select_fields = split_and_filter_fields(fields=fields)
        # For STANDARD strategy
        if self.strategy == SelectStrategy.STANDARD:
            return standard_generate_query(
                sobject=sobject, user_filter=user_filter, limit=limit, offset=offset
            )
        # For SIMILARITY strategy
        elif self.strategy == SelectStrategy.SIMILARITY:
            return similarity_generate_query(
                sobject=sobject,
                fields=select_fields,
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
        self,
        load_records,
        query_records: list,
        fields: list,
        num_records: int,
        sobject: str,
        weights: list,
        threshold: T.Union[float, None],
    ):
        # For STANDARD strategy
        if self.strategy == SelectStrategy.STANDARD:
            return standard_post_process(
                query_records=query_records, num_records=num_records, sobject=sobject
            )
        # For SIMILARITY strategy
        elif self.strategy == SelectStrategy.SIMILARITY:
            return similarity_post_process(
                load_records=load_records,
                query_records=query_records,
                fields=fields,
                sobject=sobject,
                weights=weights,
                threshold=threshold,
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
        query += f" LIMIT {limit}" if limit else ""
        query += f" OFFSET {offset}" if offset else ""
    return query, ["Id"]


def standard_post_process(
    query_records: list, num_records: int, sobject: str
) -> T.Tuple[T.List[dict], None, T.Union[str, None]]:
    """Processes the query results for the standard selection strategy"""
    # Handle case where query returns 0 records
    if not query_records:
        error_message = f"No records found for {sobject} in the target org."
        return [], None, error_message

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

    return selected_records, None, None  # Return selected records and None for error


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
        type_clause = f"TYPEOF {relationship} {' '.join(type_clauses)} ELSE Id END"
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
        query += f" LIMIT {limit}" if limit else ""
        query += f" OFFSET {offset}" if offset else ""

    # Return the original input fields with "Id" added if needed
    if "Id" not in fields:
        fields.insert(0, "Id")

    return query, fields


def similarity_post_process(
    load_records,
    query_records: list,
    fields: list,
    sobject: str,
    weights: list,
    threshold: T.Union[float, None],
) -> T.Tuple[
    T.List[T.Union[dict, None]], T.List[T.Union[list, None]], T.Union[str, None]
]:
    """Processes the query results for the similarity selection strategy"""
    # Handle case where query returns 0 records
    if not query_records and threshold is None:
        error_message = f"No records found for {sobject} in the target org."
        return [], [], error_message

    load_records = list(load_records)
    # Replace None values in each row with empty strings
    for idx, row in enumerate(load_records):
        row = [value if value is not None else "" for value in row]
        load_records[idx] = row
    load_record_count, query_record_count = len(load_records), len(query_records)

    complexity_constant = load_record_count * query_record_count

    select_records = []
    insert_records = []

    if complexity_constant < 1000 or not OPTIONAL_DEPENDENCIES_AVAILABLE:
        select_records, insert_records = levenshtein_post_process(
            load_records, query_records, fields, weights, threshold
        )
    else:
        select_records, insert_records = annoy_post_process(
            load_records, query_records, fields, weights, threshold
        )

    return select_records, insert_records, None


def annoy_post_process(
    load_records: list,
    query_records: list,
    all_fields: list,
    similarity_weights: list,
    threshold: T.Union[float, None],
) -> T.Tuple[T.List[dict], list]:
    """Processes the query results for the similarity selection strategy using Annoy algorithm for large number of records"""
    # Add warning when threshold is 0
    if threshold is not None and threshold == 0:
        logger.warning(
            "Warning: A threshold of 0 may miss exact matches in high volumes. Use a small value like 0.1 for better accuracy."
        )

    selected_records = []
    insertion_candidates = []

    # Split fields into load and select categories
    load_field_list, select_field_list = split_and_filter_fields(fields=all_fields)
    # Only select those weights for select field list
    similarity_weights = [
        similarity_weights[idx]
        for idx, field in enumerate(all_fields)
        if field in select_field_list
    ]
    load_shaped_records = reorder_records(
        records=load_records, original_fields=all_fields, new_fields=load_field_list
    )
    select_shaped_records = reorder_records(
        records=load_records, original_fields=all_fields, new_fields=select_field_list
    )

    if not query_records:
        # Directly append to load record for insertion if target_records is empty
        selected_records = [None for _ in load_records]
        insertion_candidates = load_shaped_records
        return selected_records, insertion_candidates

    hash_features = 100
    # Adjust number of trees for small datasets to avoid issues
    num_trees = max(1, min(10, len(query_records)))

    query_record_ids = [record[0] for record in query_records]
    query_record_data = [record[1:] for record in query_records]

    record_to_id_map = {
        tuple(query_record_data[i]): query_record_ids[i]
        for i in range(len(query_records))
    }

    final_load_vectors, final_query_vectors = vectorize_records(
        select_shaped_records,
        query_record_data,
        hash_features=hash_features,
        weights=similarity_weights,
    )

    # Create Annoy index for nearest neighbor search
    vector_dimension = final_query_vectors.shape[1]
    annoy_index = AnnoyIndex(vector_dimension, "euclidean")

    for i in range(len(final_query_vectors)):
        annoy_index.add_item(i, final_query_vectors[i])

    # Build the index
    annoy_index.build(num_trees)

    # Find nearest neighbors for each query vector
    # For small datasets, search more neighbors to ensure we find the best match
    n_neighbors = min(len(query_records), 2)

    for i, load_vector in enumerate(final_load_vectors):
        # Get nearest neighbors' indices and distances
        nearest_neighbors = annoy_index.get_nns_by_vector(
            load_vector, n_neighbors, include_distances=True
        )
        neighbor_indices = nearest_neighbors[0]  # Indices of nearest neighbors
        neighbor_distances = [
            distance / 2 for distance in nearest_neighbors[1]
        ]  # Distances sqrt(2(1-cos(u,v)))/2 lies between [0,1]

        # Find the best match (minimum distance)
        best_distance = neighbor_distances[0]
        best_neighbor_index = neighbor_indices[0]

        for idx in range(1, len(neighbor_indices)):
            if neighbor_distances[idx] < best_distance:
                best_distance = neighbor_distances[idx]
                best_neighbor_index = neighbor_indices[idx]

        # Use the best match
        record = query_record_data[best_neighbor_index]
        closest_record_id = record_to_id_map[tuple(record)]
        if threshold is not None and (best_distance >= threshold):
            selected_records.append(None)
            insertion_candidates.append(load_shaped_records[i])
        else:
            selected_records.append(
                {"id": closest_record_id, "success": True, "created": False}
            )

    return selected_records, insertion_candidates


def levenshtein_post_process(
    source_records: list,
    target_records: list,
    all_fields: list,
    similarity_weights: list,
    distance_threshold: T.Union[float, None],
) -> T.Tuple[T.List[T.Optional[dict]], T.List[T.Optional[list]]]:
    """Processes query results using Levenshtein algorithm for similarity selection with a small number of records."""
    selected_records = []
    insertion_candidates = []

    # Split fields into load and select categories
    load_field_list, select_field_list = split_and_filter_fields(fields=all_fields)
    # Only select those weights for select field list
    similarity_weights = [
        similarity_weights[idx]
        for idx, field in enumerate(all_fields)
        if field in select_field_list
    ]
    load_shaped_records = reorder_records(
        records=source_records, original_fields=all_fields, new_fields=load_field_list
    )
    select_shaped_records = reorder_records(
        records=source_records, original_fields=all_fields, new_fields=select_field_list
    )

    if not target_records:
        # Directly append to load record for insertion if target_records is empty
        selected_records = [None for _ in source_records]
        insertion_candidates = load_shaped_records
        return selected_records, insertion_candidates

    for select_record, load_record in zip(select_shaped_records, load_shaped_records):
        closest_match, match_distance = find_closest_record(
            select_record, target_records, similarity_weights
        )

        if distance_threshold is not None and match_distance > distance_threshold:
            # Append load record for insertion if distance exceeds threshold
            insertion_candidates.append(load_record)
            selected_records.append(None)
        elif closest_match:
            # Append match details if distance is within threshold
            selected_records.append(
                {"id": closest_match[0], "success": True, "created": False}
            )

    return selected_records, insertion_candidates


def random_post_process(
    query_records: list, num_records: int, sobject: str
) -> T.Tuple[T.List[dict], None, T.Union[str, None]]:
    """Processes the query results for the random selection strategy"""

    if not query_records:
        error_message = f"No records found for {sobject} in the target org."
        return [], None, error_message

    selected_records = []
    for _ in range(num_records):  # Loop 'num_records' times
        # Randomly select one record from query_records
        random_record = random.choice(query_records)
        selected_records.append(
            {"id": random_record[0], "success": True, "created": False}
        )

    return selected_records, None, None


def find_closest_record(load_record: list, query_records: list, weights: list):
    closest_distance = float("inf")
    closest_record = query_records[0]

    for record in query_records:
        distance = calculate_levenshtein_distance(load_record, record[1:], weights)
        if distance < closest_distance:
            closest_distance = distance
            closest_record = record

    return closest_record, closest_distance


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


def calculate_levenshtein_distance(record1: list, record2: list, weights: list):
    if len(record1) != len(record2):
        raise ValueError("Records must have the same number of fields.")
    elif len(record1) != len(weights):
        raise ValueError("Records must be same size as fields (weights).")

    total_distance = 0

    for field1, field2, weight in zip(record1, record2, weights):
        field1 = field1.lower()
        field2 = field2.lower()

        if len(field1) == 0 and len(field2) == 0:
            # If both fields are blank, distance is 0
            distance = 0
        else:
            # Average distance per character
            distance = levenshtein_distance(field1, field2) / max(
                len(field1), len(field2)
            )
            if len(field1) == 0 or len(field2) == 0:
                # If one field is blank, reduce the impact of the distance
                distance = distance * 0.05  # Fixed value for blank vs non-blank

        # Multiply the distance by the corresponding weight
        total_distance += distance * weight

    # Average distance per character with weights
    return total_distance / sum(weights) if len(weights) else 0


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


def determine_field_types(df_db, df_query, weights):
    numerical_features = []
    boolean_features = []
    categorical_features = []

    numerical_weights = []
    boolean_weights = []
    categorical_weights = []

    for col, weight in zip(df_db.columns, weights):
        # Check if the column can be converted to numeric
        try:
            temp_df_db = pd.to_numeric(df_db[col], errors="raise")
            temp_df_query = pd.to_numeric(df_query[col], errors="raise")
            # Replace empty values with 0 for numerical features
            df_db[col] = temp_df_db.fillna(0).replace("", 0)
            df_query[col] = temp_df_query.fillna(0).replace("", 0)
            numerical_features.append(col)
            numerical_weights.append(weight)
        except ValueError:
            # Check for boolean values
            if (
                df_db[col].str.lower().isin(["true", "false"]).all()
                and df_query[col].str.lower().isin(["true", "false"]).all()
            ):
                # Map to actual boolean values
                df_db[col] = df_db[col].str.lower().map({"true": True, "false": False})
                df_query[col] = (
                    df_query[col].str.lower().map({"true": True, "false": False})
                )
                boolean_features.append(col)
                boolean_weights.append(weight)
            else:
                categorical_features.append(col)
                categorical_weights.append(weight)
                # Replace empty values with 'missing' for categorical features
                df_db[col] = df_db[col].replace("", "missing")
                df_query[col] = df_query[col].replace("", "missing")

    return (
        numerical_features,
        boolean_features,
        categorical_features,
        numerical_weights,
        boolean_weights,
        categorical_weights,
    )


def vectorize_records(db_records, query_records, hash_features, weights):
    # Convert database records and query records to DataFrames
    df_db = pd.DataFrame(db_records)
    df_query = pd.DataFrame(query_records)

    # Determine field types and corresponding weights
    # Modifies boolean columns to True or False
    (
        numerical_features,
        boolean_features,
        categorical_features,
        numerical_weights,
        boolean_weights,
        categorical_weights,
    ) = determine_field_types(df_db, df_query, weights)

    # Fit StandardScaler on the numerical features of the database records
    scaler = StandardScaler()
    if numerical_features:
        df_db[numerical_features] = scaler.fit_transform(df_db[numerical_features])
        df_query[numerical_features] = scaler.transform(df_query[numerical_features])

    # For db_records
    hashed_categorical_data_db = []
    # For query_records
    hashed_categorical_data_query = []

    # Process each categorical column separately with its own HashingVectorizer
    for idx, col in enumerate(categorical_features):
        # Create a separate HashingVectorizer for each column to avoid hash collisions
        hashing_vectorizer = HashingVectorizer(
            n_features=hash_features, alternate_sign=False
        )

        # Combine all unique values from both db and query for this column to fit the vectorizer
        all_values_for_col = pd.concat([df_db[col], df_query[col]]).unique()

        # Fit the vectorizer on all unique values to ensure consistency
        hashing_vectorizer.fit(all_values_for_col)

        # Transform db and query data for this column
        hashed_db = hashing_vectorizer.transform(df_db[col]).toarray()
        hashed_query = hashing_vectorizer.transform(df_query[col]).toarray()

        # Apply weight to the hashed vectors
        hashed_db_weighted = hashed_db * categorical_weights[idx]
        hashed_query_weighted = hashed_query * categorical_weights[idx]

        hashed_categorical_data_db.append(hashed_db_weighted)
        hashed_categorical_data_query.append(hashed_query_weighted)

    # Combine all feature types into a single vector for the database records
    db_vectors = []
    if numerical_features:
        db_vectors.append(df_db[numerical_features].values * numerical_weights)
    if boolean_features:
        db_vectors.append(df_db[boolean_features].astype(int).values * boolean_weights)
    if hashed_categorical_data_db:
        db_vectors.append(np.hstack(hashed_categorical_data_db))

    # Concatenate database vectors
    final_db_vectors = np.hstack(db_vectors)

    # Combine all feature types into a single vector for the query records
    query_vectors = []
    if numerical_features:
        query_vectors.append(df_query[numerical_features].values * numerical_weights)
    if boolean_features:
        query_vectors.append(
            df_query[boolean_features].astype(int).values * boolean_weights
        )
    if hashed_categorical_data_query:
        query_vectors.append(np.hstack(hashed_categorical_data_query))

    # Concatenate query vectors
    final_query_vectors = np.hstack(query_vectors)

    return final_db_vectors, final_query_vectors


def split_and_filter_fields(fields: T.List[str]) -> T.Tuple[T.List[str], T.List[str]]:
    # List to store non-lookup fields (load fields)
    load_fields = []

    # Set to store unique first components of select fields
    unique_components = set()
    # Keep track of last flattened lookup index
    last_flat_lookup_index = -1

    # Iterate through the fields
    for idx, field in enumerate(fields):
        if "." in field:
            # Split the field by '.' and add the first component to the set
            first_component = field.split(".")[0]
            unique_components.add(first_component)
            last_flat_lookup_index = max(last_flat_lookup_index, idx)
        else:
            # Add the field to the load_fields list
            load_fields.append(field)

    # Number of unique components
    num_unique_components = len(unique_components)

    # Adjust select_fields by removing only the field at last_flat_lookup_index + 1
    if last_flat_lookup_index + 1 < len(
        fields
    ) and last_flat_lookup_index + num_unique_components < len(fields):
        select_fields = (
            fields[: last_flat_lookup_index + 1]
            + fields[last_flat_lookup_index + num_unique_components + 1 :]
        )
    else:
        select_fields = fields

    return load_fields, select_fields


# Function to reorder records based on the new field list
def reorder_records(records, original_fields, new_fields):
    if not original_fields:
        raise KeyError("original_fields should not be empty")
    # Map the original field indices
    field_index_map = {field: i for i, field in enumerate(original_fields)}
    reordered_records = []

    for record in records:
        reordered_records.append(
            [
                record[field_index_map[field]]
                for field in new_fields
                if field in field_index_map
            ]
        )

    return reordered_records
