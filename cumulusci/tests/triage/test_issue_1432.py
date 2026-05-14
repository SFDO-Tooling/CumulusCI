"""Regression repro for #1432.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``BaseTask._validate_options`` (cumulusci/core/tasks.py
around lines 187-197) only checks for *missing* required options when
the task uses the legacy ``task_options`` dict. Unknown keys are
silently accepted - passing ``-o colour red`` to a task that declares
``color`` results in no error.

The new-style Pydantic ``Options`` class path *does* reject extras
(``"extra options"`` message in the same file), so the bug is partially
mitigated for tasks that opt in. Legacy ``task_options`` dict tasks
remain affected.

The fix is to also reject unknown keys when validating the legacy
dict-style options. This test asserts the source of
``BaseTask._validate_options`` checks for unknown keys; on dev it fails
because only ``required`` is checked.
"""

import inspect

import pytest

from cumulusci.core.tasks import BaseTask


@pytest.mark.xfail(
    reason="repro for #1432 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_1432():
    src = inspect.getsource(BaseTask._validate_options)
    has_unknown_check = any(
        token in src
        for token in (
            "not in self.task_options",
            "not in task_options",
            "unknown",
            "unexpected",
            "extra option",
        )
    )
    assert has_unknown_check, (
        "BaseTask._validate_options still only checks for missing required "
        "options; unknown task_options keys are silently accepted for legacy "
        "task_options-dict tasks (see #1432)"
    )
