"""Regression repro for #2506.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: bulk operations (extract.py, load.py, step.py under
cumulusci/tasks/bulkdata/) do not respect `get_debug_mode()` the way
Snowfakery (snowfakery.py) does. The ask is to keep logs / tempfiles
when debug mode is on. snowfakery.py calls `get_debug_mode()` and logs
the tempdir per loop; the workhorse `load_dataset`/`extract_dataset`
tasks have zero references to `get_debug_mode`.

This test asserts that at least one of extract.py or load.py
references `get_debug_mode`; on dev neither does, so the assertion
fails -> XFAIL.
"""

import pathlib

import pytest

import cumulusci.tasks.bulkdata as _bulkdata_pkg


@pytest.mark.xfail(
    reason="repro for #2506 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_2506():
    pkg_path = pathlib.Path(_bulkdata_pkg.__file__).parent
    extract_src = (pkg_path / "extract.py").read_text(encoding="utf-8")
    load_src = (pkg_path / "load.py").read_text(encoding="utf-8")

    has_debug_in_workhorse = (
        "get_debug_mode" in extract_src or "get_debug_mode" in load_src
    )
    assert has_debug_in_workhorse, (
        "Neither extract.py nor load.py references get_debug_mode(); "
        "bulk operations still ignore debug-mode toggle for log/tempfile retention."
    )
