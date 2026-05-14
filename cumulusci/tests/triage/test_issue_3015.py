"""Regression repro for #3015.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `cci org remove` in cumulusci/cli/org.py:519-543
always calls `org_config.delete_org()` when `can_delete()` is
truthy. There is no `--keep-org`/`--keep` flag to detach the
keychain entry without deleting the underlying SFDX scratch
org. davisagli's documented workaround in the issue thread
(manually delete `~/.cumulusci/<project>/<org>.org`) still
applies.

This test introspects the Click command's options and asserts
that a "keep" flag exists. On dev there is no such option, so
the assertion fails -> XFAIL.
"""

import pytest

from cumulusci.cli.org import org_remove


@pytest.mark.xfail(
    reason="repro for #3015 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3015():
    option_names = {p.name for p in org_remove.params}
    has_keep_flag = any("keep" in name.lower() for name in option_names)
    assert has_keep_flag, (
        "`cci org remove` still always deletes the underlying scratch "
        f"org when can_delete(). No --keep-org flag in params={sorted(option_names)} "
        "(see #3015)."
    )
