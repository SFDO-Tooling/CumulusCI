"""Regression repro for #3663.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``FlowCoordinator._run_step`` (cumulusci/core/flowrunner.py
around lines 510-516) builds the Jinja2 context for ``when:`` from
only ``project_config`` and ``org_config``. ``self.results`` (prior-task
return values) is never exposed, so a user cannot write
``when: tasks.previous_task.return_values.foo`` in a flow ``when:``
clause - there is no codepath for that lookup at all.

The fix is to extend the Jinja2 context (e.g. include a ``tasks`` or
``steps`` mapping built from ``self.results`` keyed by task name) so
``when:`` expressions can reference prior step results, matching the
``^^task.return_value`` resolver that the option-resolution path already
supports.

This test asserts the source of ``_run_step`` references prior-step
results (``self.results``, ``tasks``, or ``steps``) inside the jinja2
context build-up. On dev it fails because the context only contains
project_config + org_config.
"""

import inspect

import pytest

from cumulusci.core.flowrunner import FlowCoordinator


@pytest.mark.xfail(
    reason="repro for #3663 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3663():
    src = inspect.getsource(FlowCoordinator._run_step)
    ctx_idx = src.find("jinja2_context")
    assert ctx_idx != -1, (
        "Source of _run_step no longer references jinja2_context; test needs updating."
    )
    end_idx = src.find("compile_expression", ctx_idx)
    if end_idx == -1:
        end_idx = len(src)
    ctx_block = src[ctx_idx:end_idx]
    has_prior_results = any(
        token in ctx_block
        for token in ("self.results", '"tasks"', "'tasks'", '"steps"', "'steps'")
    )
    assert has_prior_results, (
        "FlowCoordinator._run_step still builds the when: Jinja2 context "
        "from only project_config + org_config; prior task results "
        "(self.results) are not exposed to when: expressions"
    )
