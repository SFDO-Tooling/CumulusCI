"""Regression repro for #2951.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/bulkdata/load.py + step.py have no
PricebookEntry-aware sequencing. When a single mapping step inserts
both Standard-Price-Book PricebookEntries and custom-pricebook
PricebookEntries, Bulk API processes records in parallel batches and
Salesforce raises STANDARD_PRICE_NOT_DEFINED when a custom price is
created before the matching standard price exists. The default
extract path skips the Standard Price Book entirely (via
hardcoded_default_declarations.py), so the typical extract→load
roundtrip never hits this - but a hand-rolled mapping that includes
both does.

A real fix is either (a) split PricebookEntry steps into two
implicit batches (standard pricebook first), or (b) validate at
parse time that PricebookEntry steps are not "mixed" and surface a
clear error.

This test asserts that the loader (load.py or step.py) has some
PricebookEntry-aware sequencing/validation. On dev there is no
mention of PricebookEntry in either module, so the assertion fails
-> XFAIL.
"""

from pathlib import Path

import pytest

import cumulusci


@pytest.mark.xfail(
    reason="repro for #2951 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_2951():
    bulkdata_dir = Path(cumulusci.__file__).parent / "tasks" / "bulkdata"
    load_text = (bulkdata_dir / "load.py").read_text()
    step_text = (bulkdata_dir / "step.py").read_text()
    combined = load_text + step_text
    assert "PricebookEntry" in combined, (
        "Expected loader (load.py or step.py) to contain PricebookEntry-aware "
        "sequencing or parse-time validation; neither module references it."
    )
