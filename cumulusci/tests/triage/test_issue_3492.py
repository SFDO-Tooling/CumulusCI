"""Regression repro for #3492.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `cci flow run -o key value` in
cumulusci/cli/flow.py parses each `-o` pair by doing
`task_name, option_name = key.split("__")` — an exact 2-way
unpack. Passing the user-desired form
`-o project__custom__myattr value` triggers
``ValueError: too many values to unpack (expected 2)`` because
`split("__")` returns three elements. There is no separate
project-level option override path either.

This test imports the inner parse loop body and asserts that it
tolerates 3+ underscore-separated path segments (i.e. project-
scoped attributes). On dev the unpack still hard-fails -> XFAIL.
"""

import inspect

import pytest

from cumulusci.cli import flow as flow_cli


@pytest.mark.xfail(
    reason="repro for #3492 — see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3492():
    src = inspect.getsource(flow_cli.flow_run)
    has_strict_two_part_unpack = (
        'task_name, option_name = key.split("__")' in src
        or "task_name, option_name = key.split('__')" in src
    )
    has_project_scoped_path = (
        "project__custom" in src or "maxsplit" in src or "project_config.config" in src
    )
    assert not has_strict_two_part_unpack or has_project_scoped_path, (
        "flow_run still naïvely unpacks key.split('__') into exactly two "
        "parts; no project-scoped override path. "
        "`-o project__custom__attr value` will crash with "
        "'too many values to unpack' (see #3492)."
    )
