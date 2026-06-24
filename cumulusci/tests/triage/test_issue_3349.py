"""Regression repro for #3349.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: MappingStep.get_source_record_type_table() and
get_destination_record_type_table() in
cumulusci/tasks/bulkdata/mapping_parser.py:177-179 build the SQLite
recordtype mapping table name solely from `self.sf_object`
(`f"{self.sf_object}_rt_mapping"` and `f"{self.sf_object}_rt_target_mapping"`).
Two MappingStep entries sharing the same `sf_object` (the canonical
case is `Account` Person vs Business with different `record_type`
values) therefore collide on the same table name. load.py:552 and
extract.py:259/393 consume those names without per-step
disambiguation.

The fix is to include `self.table` (or a hash of record_type+filter)
in the generated name when multiple mapping steps share an
sf_object.

This test constructs two MappingStep objects with the same
sf_object="Account" but different record_type / table values and
asserts that the recordtype-table names differ. On dev they are
identical (collision), so the assertion fails -> XFAIL.
"""

import pytest

from cumulusci.tasks.bulkdata.mapping_parser import MappingStep


@pytest.mark.xfail(
    reason="repro for #3349 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3349():
    step_business = MappingStep(
        sf_object="Account",
        table="account_business",
        record_type="Business_Account",
        fields={"Id": "sf_id", "Name": "Name"},
    )
    step_person = MappingStep(
        sf_object="Account",
        table="account_person",
        record_type="PersonAccount",
        fields={"Id": "sf_id", "Name": "Name"},
    )

    src_business = step_business.get_source_record_type_table()
    src_person = step_person.get_source_record_type_table()
    dst_business = step_business.get_destination_record_type_table()
    dst_person = step_person.get_destination_record_type_table()

    assert src_business != src_person, (
        "Two MappingSteps sharing sf_object='Account' produced the same "
        f"source recordtype table name {src_business!r}; expected per-step "
        "disambiguation."
    )
    assert dst_business != dst_person, (
        "Two MappingSteps sharing sf_object='Account' produced the same "
        f"destination recordtype table name {dst_business!r}; expected per-step "
        "disambiguation."
    )
