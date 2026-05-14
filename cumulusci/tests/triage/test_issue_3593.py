"""Regression repro for #3593.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: SFDXOrgTask._get_command in cumulusci/tasks/sfdx.py:47-52
unconditionally appends ` -o {username}` whenever the org_config is a
ScratchOrgConfig. Some sf subcommands (e.g. `project convert source`)
do not accept a target-org flag, so the resulting command is rejected
by the sf CLI. There is no opt-out option.

The fix is either (a) a `pass_org: False` / `no_org_command` task
option, or (b) a curated whitelist of no-org sf subcommands. Either
way the bug shape is: there is currently no way to disable the
unconditional `-o` append.

This test inspects SFDXOrgTask `_get_command` source and asserts the
unconditional append has been replaced with a conditional opt-out
path (e.g., a `pass_org` option or whitelist check). On dev the
append is still unconditional, so the assertion fails -> XFAIL.
"""

import inspect

import pytest

from cumulusci.tasks.sfdx import SFDXOrgTask


@pytest.mark.xfail(
    reason="repro for #3593 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3593():
    src = inspect.getsource(SFDXOrgTask._get_command)
    options = SFDXOrgTask.task_options
    has_opt_out_option = (
        "pass_org" in options or "no_org_command" in options or "skip_org" in options
    )
    has_opt_out_in_source = (
        "pass_org" in src or "no_org_command" in src or "skip_org" in src
    )
    assert has_opt_out_option or has_opt_out_in_source, (
        "SFDXOrgTask still unconditionally appends ' -o {username}' for "
        "ScratchOrgConfig with no opt-out option. Need pass_org/no_org_command "
        f"toggle. Current _get_command:\n{src}\n"
        f"Current task_options keys: {list(options.keys())}"
    )
