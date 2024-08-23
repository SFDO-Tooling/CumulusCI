from cumulusci.tasks.bulkdata.select_utils import (
    calculate_levenshtein_distance,
    find_closest_record,
    levenshtein_distance,
    random_generate_query,
    random_post_process,
    similarity_generate_query,
    similarity_post_process,
)


# Test Cases for random_generate_query
def test_random_generate_query_with_default_record_declaration():
    sobject = "Account"  # Assuming Account has a declaration in DEFAULT_DECLARATIONS
    num_records = 5
    query, fields = random_generate_query(sobject, [], num_records)

    assert "WHERE" in query  # Ensure WHERE clause is included
    assert f"LIMIT {num_records}" in query
    assert fields == ["Id"]


def test_random_generate_query_without_default_record_declaration():
    sobject = "Contact"  # Assuming no declaration for this object
    num_records = 3
    query, fields = random_generate_query(sobject, [], num_records)

    assert "WHERE" not in query  # No WHERE clause should be present
    assert f"LIMIT {num_records}" in query
    assert fields == ["Id"]


# Test Cases for random_post_process
def test_random_post_process_with_records():
    records = [["001"], ["002"], ["003"]]
    num_records = 3
    sobject = "Contact"
    selected_records, error_message = random_post_process(
        None, records, num_records, sobject
    )

    assert error_message is None
    assert len(selected_records) == num_records
    assert all(record["success"] for record in selected_records)
    assert all(record["created"] is False for record in selected_records)
    assert all(record["id"] in ["001", "002", "003"] for record in selected_records)


def test_random_post_process_with_fewer_records():
    records = [["001"]]
    num_records = 3
    sobject = "Opportunity"
    selected_records, error_message = random_post_process(
        None, records, num_records, sobject
    )

    assert error_message is None
    assert len(selected_records) == num_records
    assert all(record["success"] for record in selected_records)
    assert all(record["created"] is False for record in selected_records)
    # Check if records are repeated to match num_records
    assert selected_records.count({"id": "001", "success": True, "created": False}) == 3


def test_random_post_process_with_no_records():
    records = []
    num_records = 2
    sobject = "Lead"
    selected_records, error_message = random_post_process(
        None, records, num_records, sobject
    )

    assert selected_records == []
    assert error_message == f"No records found for {sobject} in the target org."


# Test Cases for random_generate_query
def test_similarity_generate_query_with_default_record_declaration():
    sobject = "Account"  # Assuming Account has a declaration in DEFAULT_DECLARATIONS
    num_records = 5
    query, fields = similarity_generate_query(sobject, ["Name"], num_records)

    assert "WHERE" in query  # Ensure WHERE clause is included
    assert fields == ["Id", "Name"]


def test_similarity_generate_query_without_default_record_declaration():
    sobject = "Contact"  # Assuming no declaration for this object
    num_records = 3
    query, fields = similarity_generate_query(sobject, ["Name"], num_records)

    assert "WHERE" not in query  # No WHERE clause should be present
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


def test_calculate_levenshtein_distance():
    # Identical records
    record1 = ["Tom Cruise", "24", "Actor"]
    record2 = ["Tom Cruise", "24", "Actor"]
    assert calculate_levenshtein_distance(record1, record2) == 0  # Distance should be 0

    # Records with one different field
    record1 = ["Tom Cruise", "24", "Actor"]
    record2 = ["Tom Hanks", "24", "Actor"]
    assert calculate_levenshtein_distance(record1, record2) > 0  # Non-zero distance

    # One record has an empty field
    record1 = ["Tom Cruise", "24", "Actor"]
    record2 = ["Tom Cruise", "", "Actor"]
    assert (
        calculate_levenshtein_distance(record1, record2) > 0
    )  # Distance should reflect the empty field

    # Completely empty records
    record1 = ["", "", ""]
    record2 = ["", "", ""]
    assert calculate_levenshtein_distance(record1, record2) == 0  # Distance should be 0


def test_find_closest_record():
    # Test case 1: Exact match
    load_record = ["Tom Cruise", "62", "Actor"]
    query_records = [
        [1, "Tom Hanks", "30", "Actor"],
        [2, "Tom Cruise", "62", "Actor"],  # Exact match
        [3, "Jennifer Aniston", "30", "Actress"],
    ]
    assert find_closest_record(load_record, query_records) == [
        2,
        "Tom Cruise",
        "62",
        "Actor",
    ]  # Should return the exact match

    # Test case 2: Closest match with slight differences
    load_record = ["Tom Cruise", "62", "Actor"]
    query_records = [
        [1, "Tom Hanks", "62", "Actor"],
        [2, "Tom Cruise", "63", "Actor"],  # Slight difference
        [3, "Jennifer Aniston", "30", "Actress"],
    ]
    assert find_closest_record(load_record, query_records) == [
        2,
        "Tom Cruise",
        "63",
        "Actor",
    ]  # Should return the closest match

    # Test case 3: All records are significantly different
    load_record = ["Tom Cruise", "62", "Actor"]
    query_records = [
        [1, "Brad Pitt", "30", "Producer"],
        [2, "Leonardo DiCaprio", "40", "Director"],
        [3, "Jennifer Aniston", "30", "Actress"],
    ]
    assert (
        find_closest_record(load_record, query_records) == query_records[0]
    )  # Should return the first record as the closest (though none are close)

    # Test case 4: Closest match is the last in the list
    load_record = ["Tom Cruise", "62", "Actor"]
    query_records = [
        [1, "Johnny Depp", "50", "Actor"],
        [2, "Brad Pitt", "30", "Producer"],
        [3, "Tom Cruise", "62", "Actor"],  # Exact match as the last record
    ]
    assert find_closest_record(load_record, query_records) == [
        3,
        "Tom Cruise",
        "62",
        "Actor",
    ]  # Should return the last record

    # Test case 5: Single record in query_records
    load_record = ["Tom Cruise", "62", "Actor"]
    query_records = [[1, "Johnny Depp", "50", "Actor"]]
    assert find_closest_record(load_record, query_records) == [
        1,
        "Johnny Depp",
        "50",
        "Actor",
    ]  # Should return the only record available


def test_similarity_post_process_with_records():
    num_records = 1
    sobject = "Contact"
    load_records = [["Tom Cruise", "62", "Actor"]]
    query_records = [
        ["001", "Tom Hanks", "62", "Actor"],
        ["002", "Tom Cruise", "63", "Actor"],  # Slight difference
        ["003", "Jennifer Aniston", "30", "Actress"],
    ]

    selected_records, error_message = similarity_post_process(
        load_records, query_records, num_records, sobject
    )

    assert error_message is None
    assert len(selected_records) == num_records
    assert all(record["success"] for record in selected_records)
    assert all(record["created"] is False for record in selected_records)
    assert all(record["id"] in ["002"] for record in selected_records)


def test_similarity_post_process_with_no_records():
    records = []
    num_records = 2
    sobject = "Lead"
    selected_records, error_message = similarity_post_process(
        None, records, num_records, sobject
    )

    assert selected_records == []
    assert error_message == f"No records found for {sobject} in the target org."
