from cumulusci.tasks.bulkdata.select_utils import (
    random_generate_query,
    random_post_process,
)


# Test Cases for random_generate_query
def test_random_generate_query_with_default_record_declaration():
    sobject = "Account"  # Assuming Account has a declaration in DEFAULT_DECLARATIONS
    num_records = 5
    query, fields = random_generate_query(sobject, num_records)

    assert "WHERE" in query  # Ensure WHERE clause is included
    assert f"LIMIT {num_records}" in query
    assert fields == ["Id"]


def test_random_generate_query_without_default_record_declaration():
    sobject = "Contact"  # Assuming no declaration for this object
    num_records = 3
    query, fields = random_generate_query(sobject, num_records)

    assert "WHERE" not in query  # No WHERE clause should be present
    assert f"LIMIT {num_records}" in query
    assert fields == ["Id"]


# Test Cases for random_post_process
def test_random_post_process_with_records():
    records = [["001"], ["002"], ["003"]]
    num_records = 3
    sobject = "Contact"
    selected_records, error_message = random_post_process(records, num_records, sobject)

    assert error_message is None
    assert len(selected_records) == num_records
    assert all(record["success"] for record in selected_records)
    assert all(record["created"] is False for record in selected_records)
    assert all(record["id"] in ["001", "002", "003"] for record in selected_records)


def test_random_post_process_with_fewer_records():
    records = [["001"]]
    num_records = 3
    sobject = "Opportunity"
    selected_records, error_message = random_post_process(records, num_records, sobject)

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
    selected_records, error_message = random_post_process(records, num_records, sobject)

    assert selected_records == []
    assert error_message == f"No records found for {sobject} in the target org."
