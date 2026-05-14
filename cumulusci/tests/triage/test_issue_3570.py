"""Regression repro for #3570.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery; reverified on
origin/dev@1925a3083 - only ruff refactor since v4.10.0).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/core/flowrunner.py exposes only per-step
`ignore_failure` (mapped to `StepSpec.allow_failure`); there is no
flow-step type for `finally:` / `on_error:` / `on_failure:` /
`always_run` / `cleanup` to express "this cleanup/rollback step
should always run after the flow regardless of success or failure".
The only `finally:` in flowrunner.py is the Python `try/finally` in
FlowCoordinator.run that invokes the `post_flow` callback -
internal-only, not user-configurable.

A real fix introduces a step-level metadata flag (e.g.
`always_run: true` or a sibling `on_error:` block) and threads it
through the FlowCoordinator step-execution loop.

This test asserts that `StepSpec` exposes an "always-run" /
"on-error" attribute. On dev no such attribute exists, so the
assertion fails -> XFAIL.
"""

import pytest

from cumulusci.core.flowrunner import StepSpec


@pytest.mark.xfail(
    reason="repro for #3570 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3570():
    candidate_attrs = (
        "always_run",
        "on_error",
        "on_failure",
        "finally_step",
        "cleanup",
    )
    field_names = (
        set(StepSpec.__dataclass_fields__.keys())
        if hasattr(StepSpec, "__dataclass_fields__")
        else set(dir(StepSpec))
    )
    found = [a for a in candidate_attrs if a in field_names]
    assert found, (
        "Expected flowrunner.StepSpec to expose an always-run / on-error "
        f"affordance (one of {candidate_attrs!r}) so users can declare "
        "cleanup / rollback steps in a flow definition; none present. "
        f"Existing fields: {sorted(field_names)!r}"
    )
