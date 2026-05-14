"""Regression repro for #3699.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `ExtractData._soql_for_mapping` in
cumulusci/tasks/bulkdata/extract.py:132-146 builds the SOQL with
`WHERE` only - there is no `ORDER BY` clause. The
`MappingStep` model in
cumulusci/tasks/bulkdata/mapping_parser.py has no `order_by` /
`sort` field. The user-facing workaround (`soql_filter: "...
ORDER BY ..."`) does work via `append_filter_clause`, but the
2023 ask is for a first-class `order_by` knob to give
deterministic, diff-friendly extracts.

This test asserts that `MappingStep` declares an `order_by`
(or `sort`) field. On dev it doesn't -> XFAIL.
"""

import pytest

from cumulusci.tasks.bulkdata.mapping_parser import MappingStep


@pytest.mark.xfail(
    reason="repro for #3699 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3699():
    field_names = set(MappingStep.model_fields.keys())
    has_order_by = any(name in field_names for name in ("order_by", "sort", "sort_by"))
    assert has_order_by, (
        "MappingStep still has no first-class order_by/sort field; "
        f"declared fields: {sorted(field_names)} (see #3699)."
    )
