"""Regression repro for #3549.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `Deploy` in cumulusci/tasks/salesforce/Deploy.py
exposes `test_level` / `specified_tests` and pipes them through
to the Metadata API call but never captures or writes
runTestResult / runTestsResult into a JUnit (or JSON) file. The
2022 ask is to surface CI-consumable test artefacts directly
from `cci task run deploy`.

This test asserts that `Deploy.task_options` declares a
JUnit/test-output option key. On dev no such option exists ->
XFAIL.
"""

import pytest

from cumulusci.tasks.salesforce.Deploy import Deploy


@pytest.mark.xfail(
    reason="repro for #3549 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3549():
    options = Deploy.task_options
    has_test_output_option = any(
        any(token in key for token in ("junit", "test_output", "test_result"))
        for key in options
    )
    assert has_test_output_option, (
        "Deploy task still has no junit/test_output/test_result option; "
        f"only options: {sorted(options)} (see #3549)."
    )
