"""Regression repro for #2402.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `cci flow run` (cumulusci/cli/flow.py:119-145) only exposes
`--delete-org`; there is no `--rebuild-org` switch that would delete
the scratch org before re-running the flow against a freshly-created
one. Users currently have to chain `cci org scratch_delete X && cci
flow run X` manually.

This test asserts that the `flow run` Click command exposes a
`--rebuild-org` (or equivalent `rebuild_org` parameter). On dev no
such option exists, so the assertion fails -> XFAIL.
"""

import pytest

from cumulusci.cli.flow import flow_run


@pytest.mark.xfail(
    reason="repro for #2402 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_2402():
    param_names = {p.name for p in flow_run.params}
    assert "rebuild_org" in param_names or any(
        "rebuild-org" in flag for p in flow_run.params for flag in (p.opts or [])
    ), (
        "Expected `cci flow run` to expose a --rebuild-org option for "
        f"convenience; got params {sorted(param_names)!r}."
    )
