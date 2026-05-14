"""Regression repro for #2508.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: There is no OOTB "retry the failed records from the
previous load" feature in CumulusCI. ``load_dataset`` exposes an
``enable_rollback`` option (cumulusci/tasks/bulkdata/load.py:97-98,
``RollbackType`` enum at line 1051), but rollback **undoes** successful
inserts when failures occur — the opposite of "retry the failures".
``RowErrorChecker`` (cumulusci/tasks/bulkdata/utils.py:158) only logs
and (optionally) raises; it never persists a failed-rows artifact that
could be replayed.

The fix would be to (a) persist failed rows to a CSV/SQLite artifact
on load failure and (b) ship a ``retry_failed_load`` (or
``retry_failed_records``) task that consumes that artifact.

This test asserts ``cumulusci.yml`` declares at least one retry-named
task; on dev it fails because no such task exists.
"""

from pathlib import Path

import pytest
import yaml

import cumulusci


@pytest.mark.xfail(
    reason="repro for #2508 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_2508():
    cci_root = Path(cumulusci.__file__).parent
    with open(cci_root / "cumulusci.yml") as f:
        data = yaml.safe_load(f)

    task_names = list(data.get("tasks", {}).keys())
    retry_named = [
        n for n in task_names if "retry" in n.lower() and "failed" in n.lower()
    ]
    assert retry_named, (
        "cumulusci.yml still ships no retry-failed-records task; users have no "
        "way to re-attempt only the rows that failed in a prior load (see #2508)"
    )
