"""Regression repro for #1769.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/bulkdata/tests/test_load.py still uses the
2020-vintage pattern `lookups["Id"] = MappingLookup(name="Id",
table="accounts", key_field="sf_id")` (line 739 and several siblings:
~754, 773, 801, 1119, 1187, 1255) to describe an after-step's
UPDATE-on-Id dependency. davidmreed acknowledged in 2020 that this
is a "horrible hack" he intended to clean up; six years later it
remains in the test file.

A real fix would remove `Id` from the `lookups` dict (or stop using
`MappingLookup` to express the self-update relationship) and have
the after-step logic synthesize that relationship internally.

This test asserts that the offending pattern is absent from test_load.py.
On dev the pattern is present, so the assertion fails -> XFAIL.
"""

from pathlib import Path

import pytest

import cumulusci


@pytest.mark.xfail(
    reason="repro for #1769 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_1769():
    test_load_path = (
        Path(cumulusci.__file__).parent
        / "tasks"
        / "bulkdata"
        / "tests"
        / "test_load.py"
    )
    text = test_load_path.read_text()
    bad_pattern = 'lookups["Id"] = MappingLookup('
    assert bad_pattern not in text, (
        f"test_load.py still contains the 2020-vintage smell {bad_pattern!r}; "
        "expected the after-step Id-update relationship to be expressed "
        "without injecting a MappingLookup keyed on 'Id'."
    )
