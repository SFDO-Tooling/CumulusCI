"""Regression repro for #2507.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: there is no `undo_insert` (or similarly-named)
task. The closest mitigation is the `enable_rollback` option on
`load_data` / `snowfakery`, but that only rolls back when an
error occurs during the load — it does not provide the
post-hoc "delete everything I inserted earlier" capability the
2021 ask describes.

This test loads the universal cumulusci.yml's tasks dict and
asserts that some kind of explicit undo/cleanup task is
registered. On dev no such task exists -> XFAIL.
"""

from pathlib import Path

import pytest

import cumulusci
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load


@pytest.mark.xfail(
    reason="repro for #2507 — see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_2507():
    universal_yaml = Path(cumulusci.__file__).resolve().parent / "cumulusci.yml"
    config = cci_safe_load(universal_yaml.open(), str(universal_yaml))
    tasks = config.get("tasks", {})
    undo_task_names = [
        name for name in tasks if "undo" in name.lower() and "insert" in name.lower()
    ]
    assert undo_task_names, (
        "No `undo_insert`-style task registered; users still must "
        "manually delete records inserted by load_data (see #2507)."
    )
