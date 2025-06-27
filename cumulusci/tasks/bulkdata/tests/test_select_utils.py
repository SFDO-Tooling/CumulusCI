import pytest

from cumulusci.tasks.bulkdata.select_utils import (
    OPTIONAL_DEPENDENCIES_AVAILABLE,
    SelectOperationExecutor,
    SelectStrategy,
    add_limit_offset_to_user_filter,
    annoy_post_process,
    calculate_levenshtein_distance,
    determine_field_types,
    find_closest_record,
    levenshtein_distance,
    reorder_records,
    split_and_filter_fields,
    vectorize_records,
)

# Check for pandas availability
try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def test_standard_generate_query_without_filter():
    select_operator = SelectOperationExecutor(SelectStrategy.STANDARD)
    sobject = "Contact"  # Assuming no declaration for this object
    limit = 3
    offset = None
    query, fields = select_operator.select_generate_query(
        sobject=sobject, fields=[], user_filter="", limit=limit, offset=offset
    )

    assert f"LIMIT {limit}" in query
    assert "OFFSET" not in query
    assert fields == ["Id"]


def test_standard_generate_query_with_user_filter():
    select_operator = SelectOperationExecutor(SelectStrategy.STANDARD)
    sobject = "Contact"  # Assuming no declaration for this object
    limit = 3
    offset = None
    user_filter = "WHERE Name IN ('Sample Contact')"
    query, fields = select_operator.select_generate_query(
        sobject=sobject, fields=[], user_filter=user_filter, limit=limit, offset=offset
    )

    assert "WHERE" in query
    assert "Sample Contact" in query
    assert "LIMIT" in query
    assert "OFFSET" not in query
    assert fields == ["Id"]


def test_random_generate_query():
    select_operator = SelectOperationExecutor(SelectStrategy.RANDOM)
    sobject = "Contact"  # Assuming no declaration for this object
    limit = 3
    offset = None
    query, fields = select_operator.select_generate_query(
        sobject=sobject, fields=[], user_filter="", limit=limit, offset=offset
    )

    assert f"LIMIT {limit}" in query
    assert "OFFSET" not in query
    assert fields == ["Id"]


# Test Cases for standard_post_process
def test_standard_post_process_with_records():
    select_operator = SelectOperationExecutor(SelectStrategy.STANDARD)
    records = [["001"], ["002"], ["003"]]
    num_records = 3
    sobject = "Contact"
    selected_records, _, error_message = select_operator.select_post_process(
        load_records=None,
        query_records=records,
        num_records=num_records,
        sobject=sobject,
        weights=[],
        fields=[],
        threshold=None,
    )

    assert error_message is None
    assert len(selected_records) == num_records
    assert all(record["success"] for record in selected_records)
    assert all(record["created"] is False for record in selected_records)
    assert all(record["id"] in ["001", "002", "003"] for record in selected_records)


def test_standard_post_process_with_fewer_records():
    select_operator = SelectOperationExecutor(SelectStrategy.STANDARD)
    records = [["001"]]
    num_records = 3
    sobject = "Opportunity"
    selected_records, _, error_message = select_operator.select_post_process(
        load_records=None,
        query_records=records,
        num_records=num_records,
        sobject=sobject,
        weights=[],
        fields=[],
        threshold=None,
    )

    assert error_message is None
    assert len(selected_records) == num_records
    assert all(record["success"] for record in selected_records)
    assert all(record["created"] is False for record in selected_records)
    # Check if records are repeated to match num_records
    assert selected_records.count({"id": "001", "success": True, "created": False}) == 3


def test_standard_post_process_with_no_records():
    select_operator = SelectOperationExecutor(SelectStrategy.STANDARD)
    records = []
    num_records = 2
    sobject = "Lead"
    selected_records, _, error_message = select_operator.select_post_process(
        load_records=None,
        query_records=records,
        num_records=num_records,
        sobject=sobject,
        weights=[],
        fields=[],
        threshold=None,
    )

    assert selected_records == []
    assert error_message == f"No records found for {sobject} in the target org."


# Test cases for Random Post Process
def test_random_post_process_with_records():
    select_operator = SelectOperationExecutor(SelectStrategy.RANDOM)
    records = [["001"], ["002"], ["003"]]
    num_records = 3
    sobject = "Contact"
    selected_records, _, error_message = select_operator.select_post_process(
        load_records=None,
        query_records=records,
        num_records=num_records,
        sobject=sobject,
        weights=[],
        fields=[],
        threshold=None,
    )

    assert error_message is None
    assert len(selected_records) == num_records
    assert all(record["success"] for record in selected_records)
    assert all(record["created"] is False for record in selected_records)


def test_random_post_process_with_no_records():
    select_operator = SelectOperationExecutor(SelectStrategy.RANDOM)
    records = []
    num_records = 2
    sobject = "Lead"
    selected_records, _, error_message = select_operator.select_post_process(
        load_records=None,
        query_records=records,
        num_records=num_records,
        sobject=sobject,
        weights=[],
        fields=[],
        threshold=None,
    )

    assert selected_records == []
    assert error_message == f"No records found for {sobject} in the target org."


def test_similarity_generate_query_no_nesting():
    select_operator = SelectOperationExecutor(SelectStrategy.SIMILARITY)
    sobject = "Contact"  # Assuming no declaration for this object
    limit = 3
    offset = None
    query, fields = select_operator.select_generate_query(
        sobject, ["Name"], [], limit, offset
    )

    assert fields == ["Id", "Name"]
    assert f"LIMIT {limit}" in query
    assert "OFFSET" not in query


def test_similarity_generate_query_with_nested_fields():
    select_operator = SelectOperationExecutor(SelectStrategy.SIMILARITY)
    sobject = "Event"  # Assuming no declaration for this object
    limit = 3
    offset = None
    fields = [
        "Subject",
        "Who.Contact.Name",
        "Who.Contact.Email",
        "Who.Lead.Name",
        "Who.Lead.Company",
    ]
    query, query_fields = select_operator.select_generate_query(
        sobject, fields, [], limit, offset
    )

    assert "WHERE" not in query  # No WHERE clause should be present
    assert query_fields == [
        "Id",
        "Subject",
        "Who.Contact.Name",
        "Who.Contact.Email",
        "Who.Lead.Name",
        "Who.Lead.Company",
    ]
    assert f"LIMIT {limit}" in query
    assert "TYPEOF Who" in query
    assert "WHEN Contact" in query
    assert "WHEN Lead" in query
    assert "OFFSET" not in query


def test_random_generate_query_with_user_filter():
    select_operator = SelectOperationExecutor(SelectStrategy.SIMILARITY)
    sobject = "Contact"  # Assuming no declaration for this object
    limit = 3
    offset = None
    user_filter = "WHERE Name IN ('Sample Contact')"
    query, fields = select_operator.select_generate_query(
        sobject=sobject,
        fields=["Name"],
        user_filter=user_filter,
        limit=limit,
        offset=offset,
    )

    assert "WHERE" in query
    assert "Sample Contact" in query
    assert "LIMIT" in query
    assert "OFFSET" not in query
    assert fields == ["Id", "Name"]


def test_levenshtein_distance():
    assert levenshtein_distance("kitten", "kitten") == 0  # Identical strings
    assert levenshtein_distance("kitten", "sitten") == 1  # One substitution
    assert levenshtein_distance("kitten", "kitte") == 1  # One deletion
    assert levenshtein_distance("kitten", "sittin") == 2  # Two substitutions
    assert levenshtein_distance("kitten", "dog") == 6  # Completely different strings
    assert levenshtein_distance("kitten", "") == 6  # One string is empty
    assert levenshtein_distance("", "") == 0  # Both strings are empty
    assert levenshtein_distance("Kitten", "kitten") == 1  # Case sensitivity
    assert levenshtein_distance("kit ten", "kitten") == 1  # Strings with spaces
    assert (
        levenshtein_distance("levenshtein", "meilenstein") == 4
    )  # Longer strings with multiple differences


def test_find_closest_record_different_weights():
    load_record = ["hello", "world"]
    query_records = [
        ["record1", "hello", "word"],  # Levenshtein distance = 1
        ["record2", "hullo", "word"],  # Levenshtein distance = 1
        ["record3", "hello", "word"],  # Levenshtein distance = 1
    ]
    weights = [2.0, 0.5]

    # With different weights, the first field will have more impact
    closest_record, _ = find_closest_record(load_record, query_records, weights)
    assert closest_record == [
        "record1",
        "hello",
        "word",
    ], "The closest record should be 'record1'."


def test_find_closest_record_basic():
    load_record = ["hello", "world"]
    query_records = [
        ["record1", "hello", "word"],  # Levenshtein distance = 1
        ["record2", "hullo", "word"],  # Levenshtein distance = 1
        ["record3", "hello", "word"],  # Levenshtein distance = 1
    ]
    weights = [1.0, 1.0]

    closest_record, _ = find_closest_record(load_record, query_records, weights)
    assert closest_record == [
        "record1",
        "hello",
        "word",
    ], "The closest record should be 'record1'."


def test_find_closest_record_multiple_matches():
    load_record = ["cat", "dog"]
    query_records = [
        ["record1", "bat", "dog"],  # Levenshtein distance = 1
        ["record2", "cat", "dog"],  # Levenshtein distance = 0
        ["record3", "dog", "cat"],  # Levenshtein distance = 3
    ]
    weights = [1.0, 1.0]

    closest_record, _ = find_closest_record(load_record, query_records, weights)
    assert closest_record == [
        "record2",
        "cat",
        "dog",
    ], "The closest record should be 'record2'."


def test_similarity_post_process_with_records():
    select_operator = SelectOperationExecutor(SelectStrategy.SIMILARITY)
    num_records = 1
    sobject = "Contact"
    load_records = [["Tom Cruise", "62", "Actor"]]
    query_records = [
        ["001", "Bob Hanks", "62", "Actor"],
        ["002", "Tom Cruise", "63", "Actor"],  # Slight difference
        ["003", "Jennifer Aniston", "30", "Actress"],
    ]

    weights = [1.0, 1.0, 1.0]  # Adjust weights to match your data structure

    selected_records, _, error_message = select_operator.select_post_process(
        load_records=load_records,
        query_records=query_records,
        num_records=num_records,
        sobject=sobject,
        weights=weights,
        fields=["Name", "Age", "Occupation"],
        threshold=None,
    )

    assert error_message is None
    assert len(selected_records) == num_records
    assert all(record["success"] for record in selected_records)
    assert all(record["created"] is False for record in selected_records)
    x = [record["id"] for record in selected_records]
    print(x)
    assert all(record["id"] in ["002"] for record in selected_records)


def test_similarity_post_process_with_no_records():
    select_operator = SelectOperationExecutor(SelectStrategy.SIMILARITY)
    records = []
    num_records = 2
    sobject = "Lead"
    selected_records, _, error_message = select_operator.select_post_process(
        load_records=None,
        query_records=records,
        num_records=num_records,
        sobject=sobject,
        weights=[1, 1, 1],
        fields=[],
        threshold=None,
    )

    assert selected_records == []
    assert error_message == f"No records found for {sobject} in the target org."


def test_similarity_post_process_with_no_records__zero_threshold():
    select_operator = SelectOperationExecutor(SelectStrategy.SIMILARITY)
    load_records = [["Aditya", "Salesforce"], ["Jawad", "Salesforce"]]
    query_records = []
    num_records = 2
    sobject = "Lead"
    (
        selected_records,
        insert_records,
        error_message,
    ) = select_operator.select_post_process(
        load_records=load_records,
        query_records=query_records,
        num_records=num_records,
        sobject=sobject,
        weights=[1, 1, 1],
        fields=["LastName", "Company"],
        threshold=0,
    )

    # Assert that it inserts everything
    assert selected_records == [None, None]
    assert insert_records[0] == ["Aditya", "Salesforce"]
    assert insert_records[1] == ["Jawad", "Salesforce"]
    assert error_message is None


def test_calculate_levenshtein_distance_basic():
    record1 = ["hello", "world"]
    record2 = ["hullo", "word"]
    weights = [1.0, 1.0]

    # Expected distance based on simple Levenshtein distances
    # Levenshtein("hello", "hullo") = 1, Levenshtein("world", "word") = 1
    expected_distance = (1 / 5 * 1.0 + 1 / 5 * 1.0) / 2  # Averaged over two fields

    result = calculate_levenshtein_distance(record1, record2, weights)
    assert result == pytest.approx(
        expected_distance
    ), "Basic distance calculation failed."

    # Empty fields
    record1 = ["hello", ""]
    record2 = ["hullo", ""]
    weights = [1.0, 1.0]

    # Expected distance based on simple Levenshtein distances
    # Levenshtein("hello", "hullo") = 1, Levenshtein("", "") = 0
    expected_distance = (1 / 5 * 1.0 + 0 * 1.0) / 2  # Averaged over two fields

    result = calculate_levenshtein_distance(record1, record2, weights)
    assert result == pytest.approx(
        expected_distance
    ), "Basic distance calculation with empty fields failed."

    # Partial empty fields
    record1 = ["hello", "world"]
    record2 = ["hullo", ""]
    weights = [1.0, 1.0]

    # Expected distance based on simple Levenshtein distances
    # Levenshtein("hello", "hullo") = 1, Levenshtein("world", "") = 5
    expected_distance = (
        1 / 5 * 1.0 + 5 / 5 * 0.05 * 1.0
    ) / 2  # Averaged over two fields

    result = calculate_levenshtein_distance(record1, record2, weights)
    assert result == pytest.approx(
        expected_distance
    ), "Basic distance calculation with partial empty fields failed."


def test_calculate_levenshtein_distance_weighted():
    record1 = ["cat", "dog"]
    record2 = ["bat", "fog"]
    weights = [2.0, 0.5]

    # Levenshtein("cat", "bat") = 1, Levenshtein("dog", "fog") = 1
    expected_distance = (
        1 / 3 * 2.0 + 1 / 3 * 0.5
    ) / 2.5  # Weighted average over two fields

    result = calculate_levenshtein_distance(record1, record2, weights)
    assert result == pytest.approx(
        expected_distance
    ), "Weighted distance calculation failed."


def test_calculate_levenshtein_distance_records_length_doesnt_match():
    record1 = ["cat", "dog", "cow"]
    record2 = ["bat", "fog"]
    weights = [2.0, 0.5]

    with pytest.raises(ValueError) as e:
        calculate_levenshtein_distance(record1, record2, weights)
    assert "Records must have the same number of fields." in str(e.value)


def test_calculate_levenshtein_distance_weights_length_doesnt_match():
    record1 = ["cat", "dog"]
    record2 = ["bat", "fog"]
    weights = [2.0, 0.5, 3.0]

    with pytest.raises(ValueError) as e:
        calculate_levenshtein_distance(record1, record2, weights)
    assert "Records must be same size as fields (weights)." in str(e.value)


@pytest.mark.skipif(
    not PANDAS_AVAILABLE or not OPTIONAL_DEPENDENCIES_AVAILABLE,
    reason="requires optional dependencies for annoy",
)
def test_all_numeric_columns():
    df_db = pd.DataFrame({"A": ["1", "2", "3"], "B": ["4.5", " 5.5", "6.5"]})
    df_query = pd.DataFrame({"A": ["4", "5", ""], "B": ["4.5", "5.5", "6.5"]})
    weights = [0.1, 0.2]
    expected_output = (
        ["A", "B"],  # numerical_features
        [],  # boolean_features
        [],  # categorical_features
        [0.1, 0.2],  # numerical_weights
        [],  # boolean_weights
        [],  # categorical_weights
    )
    assert determine_field_types(df_db, df_query, weights) == expected_output


@pytest.mark.skipif(
    not PANDAS_AVAILABLE or not OPTIONAL_DEPENDENCIES_AVAILABLE,
    reason="requires optional dependencies for annoy",
)
def test_numeric_columns__one_non_numeric():
    df_db = pd.DataFrame({"A": ["1", "2", "3"], "B": ["4.5", "5.5", "6.5"]})
    df_query = pd.DataFrame({"A": ["4", "5", "6"], "B": ["abcd", "5.5", "6.5"]})
    weights = [0.1, 0.2]
    expected_output = (
        ["A"],  # numerical_features
        [],  # boolean_features
        ["B"],  # categorical_features
        [0.1],  # numerical_weights
        [],  # boolean_weights
        [0.2],  # categorical_weights
    )
    assert determine_field_types(df_db, df_query, weights) == expected_output


@pytest.mark.skipif(
    not PANDAS_AVAILABLE or not OPTIONAL_DEPENDENCIES_AVAILABLE,
    reason="requires optional dependencies for annoy",
)
def test_all_boolean_columns():
    df_db = pd.DataFrame(
        {"A": ["true", "false", "true"], "B": ["false", "true", "false"]}
    )
    df_query = pd.DataFrame(
        {"A": ["true", "false", "true"], "B": ["false", "true", "false"]}
    )
    weights = [0.3, 0.4]
    expected_output = (
        [],  # numerical_features
        ["A", "B"],  # boolean_features
        [],  # categorical_features
        [],  # numerical_weights
        [0.3, 0.4],  # boolean_weights
        [],  # categorical_weights
    )
    assert determine_field_types(df_db, df_query, weights) == expected_output


@pytest.mark.skipif(
    not PANDAS_AVAILABLE or not OPTIONAL_DEPENDENCIES_AVAILABLE,
    reason="requires optional dependencies for annoy",
)
def test_all_categorical_columns():
    df_db = pd.DataFrame(
        {"A": ["apple", "banana", "cherry"], "B": ["dog", "cat", "mouse"]}
    )
    df_query = pd.DataFrame(
        {"A": ["banana", "apple", "cherry"], "B": ["cat", "dog", "mouse"]}
    )
    weights = [0.5, 0.6]
    expected_output = (
        [],  # numerical_features
        [],  # boolean_features
        ["A", "B"],  # categorical_features
        [],  # numerical_weights
        [],  # boolean_weights
        [0.5, 0.6],  # categorical_weights
    )
    assert determine_field_types(df_db, df_query, weights) == expected_output


@pytest.mark.skipif(
    not PANDAS_AVAILABLE or not OPTIONAL_DEPENDENCIES_AVAILABLE,
    reason="requires optional dependencies for annoy",
)
def test_mixed_types():
    df_db = pd.DataFrame(
        {
            "A": ["1", "2", "3"],
            "B": ["true", "false", "true"],
            "C": ["apple", "banana", "cherry"],
        }
    )
    df_query = pd.DataFrame(
        {
            "A": ["1", "3", ""],
            "B": ["true", "true", "true"],
            "C": ["apple", "", "3"],
        }
    )
    weights = [0.7, 0.8, 0.9]
    expected_output = (
        ["A"],  # numerical_features
        ["B"],  # boolean_features
        ["C"],  # categorical_features
        [0.7],  # numerical_weights
        [0.8],  # boolean_weights
        [0.9],  # categorical_weights
    )
    assert determine_field_types(df_db, df_query, weights) == expected_output


@pytest.mark.skipif(
    not PANDAS_AVAILABLE or not OPTIONAL_DEPENDENCIES_AVAILABLE,
    reason="requires optional dependencies for annoy",
)
def test_vectorize_records_mixed_numerical_boolean_categorical():
    # Test data with mixed types: numerical and categorical only
    db_records = [["1.0", "true", "apple"], ["2.0", "false", "banana"]]
    query_records = [["1.5", "true", "apple"], ["2.5", "false", "cherry"]]
    weights = [1.0, 1.0, 1.0]  # Equal weights for numerical and categorical columns
    hash_features = 4  # Number of hashing vectorizer features for categorical columns

    final_db_vectors, final_query_vectors = vectorize_records(
        db_records, query_records, hash_features, weights
    )

    # Check the shape of the output vectors
    assert final_db_vectors.shape[0] == len(db_records), "DB vectors row count mismatch"
    assert final_query_vectors.shape[0] == len(
        query_records
    ), "Query vectors row count mismatch"

    # Expected dimensions: numerical (1) + categorical hashed features (4)
    expected_feature_count = 2 + hash_features
    assert (
        final_db_vectors.shape[1] == expected_feature_count
    ), "DB vectors column count mismatch"
    assert (
        final_query_vectors.shape[1] == expected_feature_count
    ), "Query vectors column count mismatch"


@pytest.mark.skipif(
    not PANDAS_AVAILABLE or not OPTIONAL_DEPENDENCIES_AVAILABLE,
    reason="requires optional dependencies for annoy",
)
def test_annoy_post_process():
    # Test data
    load_records = [["Alice", "Engineer"], ["Bob", "Doctor"]]
    query_records = [["q1", "Alice", "Engineer"], ["q2", "Charlie", "Artist"]]
    weights = [1.0, 1.0, 1.0]  # Example weights

    closest_records, insert_records = annoy_post_process(
        load_records=load_records,
        query_records=query_records,
        similarity_weights=weights,
        all_fields=["Name", "Occupation"],
        threshold=None,
    )

    # Assert the closest records
    assert (
        len(closest_records) == 2
    )  # We expect two results (one for each query record)
    assert (
        closest_records[0]["id"] == "q1"
    )  # The first query record should match the first load record

    # No errors expected
    assert not insert_records


@pytest.mark.skipif(
    not PANDAS_AVAILABLE or not OPTIONAL_DEPENDENCIES_AVAILABLE,
    reason="requires optional dependencies for annoy",
)
def test_annoy_post_process__insert_records():
    # Test data
    load_records = [["Alice", "Engineer"], ["Bob", "Doctor"]]
    query_records = [["q1", "Alice", "Engineer"], ["q2", "Charlie", "Artist"]]
    weights = [1.0, 1.0, 1.0]  # Example weights
    threshold = 0.3

    closest_records, insert_records = annoy_post_process(
        load_records=load_records,
        query_records=query_records,
        similarity_weights=weights,
        all_fields=["Name", "Occupation"],
        threshold=threshold,
    )

    # Assert the closest records
    assert len(closest_records) == 2  # We expect two results (one for each load record)

    # Count matches vs insertions
    matches = [record for record in closest_records if record is not None]
    insertions = [record for record in closest_records if record is None]

    # We should have some matches or insertions
    assert len(matches) + len(insertions) == 2

    # Check that matches have the correct structure
    for match in matches:
        assert "id" in match
        assert match["success"] is True
        assert match["created"] is False
        assert match["id"] in ["q1", "q2"]

    # The number of insertions should match the number of None values in closest_records
    assert len(insert_records) == len(insertions)

    # Each insertion record should match the structure expected
    for insert_record in insert_records:
        assert len(insert_record) == 2  # Name and Occupation
        assert insert_record in [["Alice", "Engineer"], ["Bob", "Doctor"]]


def test_annoy_post_process__no_query_records():
    # Test data
    load_records = [["Alice", "Engineer"], ["Bob", "Doctor"]]
    query_records = []
    weights = [1.0, 1.0, 1.0]  # Example weights
    threshold = 0.3

    closest_records, insert_records = annoy_post_process(
        load_records=load_records,
        query_records=query_records,
        similarity_weights=weights,
        all_fields=["Name", "Occupation"],
        threshold=threshold,
    )

    # Assert the closest records
    assert len(closest_records) == 2  # We expect two results (both None)
    assert all(rec is None for rec in closest_records)  # Both should be None
    assert insert_records[0] == [
        "Alice",
        "Engineer",
    ]  # The first insert record should match the second load record
    assert insert_records[1] == [
        "Bob",
        "Doctor",
    ]  # The first insert record should match the second load record


@pytest.mark.skipif(
    not PANDAS_AVAILABLE or not OPTIONAL_DEPENDENCIES_AVAILABLE,
    reason="requires optional dependencies for annoy",
)
def test_annoy_post_process__insert_records_with_polymorphic_fields():
    # Test data
    load_records = [
        ["Alice", "Engineer", "Alice_Contact", "abcd1234"],
        ["Bob", "Doctor", "Bob_Contact", "qwer1234"],
    ]
    query_records = [
        ["q1", "Alice", "Engineer", "Alice_Contact"],
        ["q2", "Charlie", "Artist", "Charlie_Contact"],
    ]
    weights = [1.0, 1.0, 1.0, 1.0]  # Example weights
    threshold = 0.3
    all_fields = ["Name", "Occupation", "Contact.Name", "ContactId"]

    closest_records, insert_records = annoy_post_process(
        load_records=load_records,
        query_records=query_records,
        similarity_weights=weights,
        all_fields=all_fields,
        threshold=threshold,
    )

    # Assert the closest records
    assert len(closest_records) == 2  # We expect two results (one for each load record)

    # Count matches vs insertions
    matches = [record for record in closest_records if record is not None]
    insertions = [record for record in closest_records if record is None]

    # We should have some matches or insertions
    assert len(matches) + len(insertions) == 2

    # Check that matches have the correct structure
    for match in matches:
        assert "id" in match
        assert match["success"] is True
        assert match["created"] is False
        assert match["id"] in ["q1", "q2"]

    # The number of insertions should match the number of None values in closest_records
    assert len(insert_records) == len(insertions)

    # Each insertion record should have the polymorphic field filtered out
    # (ContactId should be removed, but Contact.Name lookup field should remain)
    for insert_record in insert_records:
        assert len(insert_record) == 3  # Name, Occupation, ContactId (load fields)
        # Should be one of the original load records but with ContactId field
        assert insert_record in [
            ["Alice", "Engineer", "abcd1234"],
            ["Bob", "Doctor", "qwer1234"],
        ]


@pytest.mark.skipif(
    not PANDAS_AVAILABLE or not OPTIONAL_DEPENDENCIES_AVAILABLE,
    reason="requires optional dependencies for annoy",
)
def test_single_record_match_annoy_post_process():
    # Mock data where only the first query record matches the first load record
    load_records = [["Alice", "Engineer"], ["Bob", "Doctor"]]
    query_records = [["q1", "Alice", "Engineer"]]
    weights = [1.0, 1.0, 1.0]

    closest_records, insert_records = annoy_post_process(
        load_records=load_records,
        query_records=query_records,
        similarity_weights=weights,
        all_fields=["Name", "Occupation"],
        threshold=None,
    )

    # Both the load records should be matched with the only query record we have
    assert len(closest_records) == 2
    assert closest_records[0]["id"] == "q1"
    assert not insert_records


@pytest.mark.parametrize(
    "filter_clause, limit_clause, offset_clause, expected",
    [
        # Test: No existing LIMIT/OFFSET and no new clauses
        ("SELECT * FROM users", None, None, " SELECT * FROM users"),
        # Test: Existing LIMIT and no new limit provided
        ("SELECT * FROM users LIMIT 100", None, None, "SELECT * FROM users LIMIT 100"),
        # Test: Existing OFFSET and no new offset provided
        ("SELECT * FROM users OFFSET 20", None, None, "SELECT * FROM users OFFSET 20"),
        # Test: Existing LIMIT/OFFSET and new clauses provided
        (
            "SELECT * FROM users LIMIT 100 OFFSET 20",
            50,
            10,
            "SELECT * FROM users LIMIT 50 OFFSET 30",
        ),
        # Test: Existing LIMIT, new limit larger than existing (should keep the smaller one)
        ("SELECT * FROM users LIMIT 100", 150, None, "SELECT * FROM users LIMIT 100"),
        # Test: New limit smaller than existing (should use the new one)
        ("SELECT * FROM users LIMIT 100", 50, None, "SELECT * FROM users LIMIT 50"),
        # Test: Existing OFFSET, adding a new offset (should sum the offsets)
        ("SELECT * FROM users OFFSET 20", None, 30, "SELECT * FROM users OFFSET 50"),
        # Test: Existing LIMIT/OFFSET and new values set to None
        (
            "SELECT * FROM users LIMIT 100 OFFSET 20",
            None,
            None,
            "SELECT * FROM users LIMIT 100 OFFSET 20",
        ),
        # Test: Removing existing LIMIT and adding a new one
        ("SELECT * FROM users LIMIT 200", 50, None, "SELECT * FROM users LIMIT 50"),
        # Test: Removing existing OFFSET and adding a new one
        ("SELECT * FROM users OFFSET 40", None, 20, "SELECT * FROM users OFFSET 60"),
        # Edge case: Filter clause with mixed cases
        (
            "SELECT * FROM users LiMiT 100 oFfSeT 20",
            50,
            10,
            "SELECT * FROM users LIMIT 50 OFFSET 30",
        ),
        # Test: Filter clause with trailing/leading spaces
        (
            "   SELECT * FROM users   LIMIT 100   OFFSET 20   ",
            50,
            10,
            "SELECT * FROM users LIMIT 50 OFFSET 30",
        ),
    ],
)
def test_add_limit_offset_to_user_filter(
    filter_clause, limit_clause, offset_clause, expected
):
    result = add_limit_offset_to_user_filter(filter_clause, limit_clause, offset_clause)
    assert result.strip() == expected.strip()


def test_reorder_records_basic_reordering():
    records = [
        ["Alice", 30, "Engineer"],
        ["Bob", 25, "Designer"],
    ]
    original_fields = ["name", "age", "job"]
    new_fields = ["job", "name"]

    expected = [
        ["Engineer", "Alice"],
        ["Designer", "Bob"],
    ]
    result = reorder_records(records, original_fields, new_fields)
    assert result == expected


def test_reorder_records_partial_fields():
    records = [
        ["Alice", 30, "Engineer"],
        ["Bob", 25, "Designer"],
    ]
    original_fields = ["name", "age", "job"]
    new_fields = ["age"]

    expected = [
        [30],
        [25],
    ]
    result = reorder_records(records, original_fields, new_fields)
    assert result == expected


def test_reorder_records_missing_fields_in_new_fields():
    records = [
        ["Alice", 30, "Engineer"],
        ["Bob", 25, "Designer"],
    ]
    original_fields = ["name", "age", "job"]
    new_fields = ["nonexistent", "job"]

    expected = [
        ["Engineer"],
        ["Designer"],
    ]
    result = reorder_records(records, original_fields, new_fields)
    assert result == expected


def test_reorder_records_empty_records():
    records = []
    original_fields = ["name", "age", "job"]
    new_fields = ["job", "name"]

    expected = []
    result = reorder_records(records, original_fields, new_fields)
    assert result == expected


def test_reorder_records_empty_new_fields():
    records = [
        ["Alice", 30, "Engineer"],
        ["Bob", 25, "Designer"],
    ]
    original_fields = ["name", "age", "job"]
    new_fields = []

    expected = [
        [],
        [],
    ]
    result = reorder_records(records, original_fields, new_fields)
    assert result == expected


def test_reorder_records_empty_original_fields():
    records = [
        ["Alice", 30, "Engineer"],
        ["Bob", 25, "Designer"],
    ]
    original_fields = []
    new_fields = ["job", "name"]

    with pytest.raises(KeyError):
        reorder_records(records, original_fields, new_fields)


def test_reorder_records_no_common_fields():
    records = [
        ["Alice", 30, "Engineer"],
        ["Bob", 25, "Designer"],
    ]
    original_fields = ["name", "age", "job"]
    new_fields = ["nonexistent_field"]

    expected = [
        [],
        [],
    ]
    result = reorder_records(records, original_fields, new_fields)
    assert result == expected


def test_reorder_records_duplicate_fields_in_new_fields():
    records = [
        ["Alice", 30, "Engineer"],
        ["Bob", 25, "Designer"],
    ]
    original_fields = ["name", "age", "job"]
    new_fields = ["job", "job", "name"]

    expected = [
        ["Engineer", "Engineer", "Alice"],
        ["Designer", "Designer", "Bob"],
    ]
    result = reorder_records(records, original_fields, new_fields)
    assert result == expected


def test_reorder_records_all_fields_in_order():
    records = [
        ["Alice", 30, "Engineer"],
        ["Bob", 25, "Designer"],
    ]
    original_fields = ["name", "age", "job"]
    new_fields = ["name", "age", "job"]

    expected = [
        ["Alice", 30, "Engineer"],
        ["Bob", 25, "Designer"],
    ]
    result = reorder_records(records, original_fields, new_fields)
    assert result == expected


def test_split_and_filter_fields_basic_case():
    fields = [
        "Account.Name",
        "Account.Industry",
        "Contact.Name",
        "AccountId",
        "ContactId",
        "CreatedDate",
    ]
    load_fields, select_fields = split_and_filter_fields(fields)
    assert load_fields == ["AccountId", "ContactId", "CreatedDate"]
    assert select_fields == [
        "Account.Name",
        "Account.Industry",
        "Contact.Name",
        "CreatedDate",
    ]


def test_split_and_filter_fields_all_non_lookup_fields():
    fields = ["Name", "CreatedDate"]
    load_fields, select_fields = split_and_filter_fields(fields)
    assert load_fields == ["Name", "CreatedDate"]
    assert select_fields == fields


def test_split_and_filter_fields_all_lookup_fields():
    fields = ["Account.Name", "Account.Industry", "Contact.Name"]
    load_fields, select_fields = split_and_filter_fields(fields)
    assert load_fields == []
    assert select_fields == fields


def test_split_and_filter_fields_empty_fields():
    fields = []
    load_fields, select_fields = split_and_filter_fields(fields)
    assert load_fields == []
    assert select_fields == []


def test_split_and_filter_fields_single_non_lookup_field():
    fields = ["Id"]
    load_fields, select_fields = split_and_filter_fields(fields)
    assert load_fields == ["Id"]
    assert select_fields == ["Id"]


def test_split_and_filter_fields_single_lookup_field():
    fields = ["Account.Name"]
    load_fields, select_fields = split_and_filter_fields(fields)
    assert load_fields == []
    assert select_fields == ["Account.Name"]


def test_split_and_filter_fields_multiple_unique_lookups():
    fields = [
        "Account.Name",
        "Account.Industry",
        "Contact.Email",
        "Contact.Phone",
        "Id",
    ]
    load_fields, select_fields = split_and_filter_fields(fields)
    assert load_fields == ["Id"]
    assert (
        select_fields == fields
    )  # No filtering applied since all components are unique
