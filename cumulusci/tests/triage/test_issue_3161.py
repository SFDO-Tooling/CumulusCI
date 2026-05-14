"""Regression repro for #3161.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: flowrunner.py:300-320 supports masking task options via
`info.get("sensitive")`, but the Robot `vars` option in
cumulusci/tasks/robotframework/robotframework.py:54-56 is NOT marked
`sensitive: True`. The user's specific request — mask multi-line
GitHub Actions secrets passed via `-o robot__vars …` — is therefore
not protected by the existing infrastructure.

The minimal fix is to mark Robot's `vars` option `sensitive: True`
(or expose a CLI/flow-side hide flag).

This test imports the Robot task class and asserts the `vars` option
declares `sensitive: True`. On dev it does not, so the assertion
fails -> XFAIL.
"""

import pytest

from cumulusci.tasks.robotframework.robotframework import Robot


@pytest.mark.xfail(
    reason="repro for #3161 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3161():
    vars_option = Robot.task_options.get("vars", {})
    assert vars_option.get("sensitive") is True, (
        "Robot task_options['vars'] is not marked sensitive; -o robot__vars "
        f"values are logged in plaintext. Current option metadata: {vars_option!r}"
    )
