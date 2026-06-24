"""Regression repro for #3746.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery; reverified on
origin/dev@1925a3083 - only ruff refactor since v4.10.0).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/create_package_version.py
`_get_base_version_number` (L529-545) issues a Tooling API SOQL
against Package2Version with no `IsDeprecated = false` filter:

    SELECT MajorVersion, MinorVersion, PatchVersion, BuildNumber,
           IsReleased
    FROM Package2Version
    WHERE Package2Id='{package_id}'
    ORDER BY MajorVersion DESC, MinorVersion DESC, ...
    LIMIT 1

If the highest version was deleted (sf package version delete), the
deprecated row is still returned, so the next version-bump bases off
of a soft-deleted version. The same file at L297 DOES include
`IsDeprecated = FALSE` for `Package2` lookups, so the project knows
about the column - the omission at L535 is asymmetric and matches
the report exactly.

A real fix is a single-line SOQL change: add
`AND IsDeprecated = false` to the WHERE clause.

This test reads create_package_version.py and asserts the
`Package2Version` SOQL filters on `IsDeprecated`. On dev it does
not, so the assertion fails -> XFAIL.
"""

from pathlib import Path

import pytest

import cumulusci


@pytest.mark.xfail(
    reason="repro for #3746 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3746():
    src_path = Path(cumulusci.__file__).parent / "tasks" / "create_package_version.py"
    text = src_path.read_text()
    # Locate the _get_base_version_number SOQL block. It is the only
    # Package2Version SOQL that ORDERs BY MajorVersion DESC ... LIMIT 1.
    needle = "ORDER BY MajorVersion DESC"
    assert needle in text, "expected the _get_base_version_number SOQL block"
    block_start = text.rindex("FROM Package2Version", 0, text.index(needle))
    block_end = text.index("LIMIT 1", block_start) + len("LIMIT 1")
    block = text[block_start:block_end].lower()
    assert "isdeprecated" in block, (
        "Expected `_get_base_version_number` Package2Version SOQL to filter "
        "on IsDeprecated = false (matching the Package2 lookup at L297); the "
        f"current WHERE clause has no IsDeprecated filter: {text[block_start:block_end]!r}"
    )
