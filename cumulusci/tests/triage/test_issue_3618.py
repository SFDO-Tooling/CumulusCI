"""Regression repro for #3618.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `cci org remove` and `cci org scratch_delete` both
take a single `org_name` argument via
`orgname_option_or_argument(required=True)` (Click
`@click.argument` with no `nargs=-1`, no comma-split helper).
The user ask is to accept a list of org names in one invocation
so a CI step can clean up several scratch orgs at once.

This test introspects the Click commands and asserts that the
`orgname` argument accepts >1 value (either `nargs=-1` or a
list-coerced custom callback). On dev neither command opts in
-> XFAIL.
"""

import pytest

from cumulusci.cli.org import org_remove, org_scratch_delete


def _orgname_param(cmd):
    for param in cmd.params:
        if param.name == "orgname":
            return param
    return None


@pytest.mark.xfail(
    reason="repro for #3618 — see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3618():
    for cmd in (org_remove, org_scratch_delete):
        param = _orgname_param(cmd)
        assert param is not None, (
            f"{cmd.name}: expected an 'orgname' click.Argument, none found"
        )
        accepts_many = getattr(param, "nargs", 1) in (-1,) or getattr(
            param, "multiple", False
        )
        assert accepts_many, (
            f"`cci org {cmd.name}` orgname argument still accepts only a "
            f"single value (nargs={getattr(param, 'nargs', 1)}). #3618 "
            "asks for list/batch support."
        )
