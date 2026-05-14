"""Regression repro for #3470.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``cumulusci/cumulusci.yml`` still defines only the
``ci_master`` flow (line 823); no ``ci_main`` alias exists.
``rg ci_main`` returns no matches. davidmreed's 2022 reply indicates
this needs flow-aliasing infrastructure first.

The fix is either (a) to add a flow-aliasing mechanism and then
register ``ci_main`` as an alias for ``ci_master``, or (b) ship an
inclusive-named ``ci_main`` flow alongside ``ci_master`` (perhaps
deprecating ``ci_master`` over time).

This test asserts ``ci_main`` is a recognized flow name in
cumulusci.yml; on dev it fails because only ``ci_master`` exists.
"""

from pathlib import Path

import pytest
import yaml

import cumulusci


@pytest.mark.xfail(
    reason="repro for #3470 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3470():
    cci_root = Path(cumulusci.__file__).parent
    with open(cci_root / "cumulusci.yml") as f:
        data = yaml.safe_load(f)

    flow_names = set(data.get("flows", {}).keys())
    assert "ci_main" in flow_names, (
        "cumulusci.yml still defines only ci_master; no ci_main alias / flow "
        f"exists. Flows present: {sorted(flow_names)} (see #3470)"
    )
