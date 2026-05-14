"""Regression repro for #3506.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``FlowCoordinator._visit_step``
(cumulusci/core/flowrunner.py) only wires ``when=step_config.get("when")``
on the ``task:`` branch (around line 669). The ``flow:`` branch
(around lines 674-697) recurses into nested steps without ever reading
``step_config.get("when")`` - so a ``when:`` clause attached to a
``flow:`` step is silently dropped.

The fix is to propagate the parent flow-step's ``when:`` down to the
nested StepSpecs (most simply by AND-ing it into each child's ``when``,
or by gating the recursive ``_visit_step`` call on it). This test
asserts the source of ``_visit_step`` references ``step_config.get(\"when\")``
inside the ``"flow" in step_config`` branch; on dev it fails because
that branch does not read ``when``.
"""

import inspect

import pytest

from cumulusci.core.flowrunner import FlowCoordinator


@pytest.mark.xfail(
    reason="repro for #3506 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3506():
    src = inspect.getsource(FlowCoordinator._visit_step)
    flow_idx = src.find('if "flow" in step_config')
    assert flow_idx != -1, (
        "Source of _visit_step no longer has the recognizable "
        '`if "flow" in step_config:` branch; test needs updating.'
    )
    flow_branch = src[flow_idx:]
    has_when = ('step_config.get("when"' in flow_branch) or (
        "step_config.get('when'" in flow_branch
    )
    assert has_when, (
        "flow:-step branch in FlowCoordinator._visit_step still ignores "
        "step_config.get('when'); when: clauses on flow steps are silently dropped"
    )
