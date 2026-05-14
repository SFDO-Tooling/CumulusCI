"""Regression repro for #808.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: UninstallPackaged._init_options() at
cumulusci/tasks/salesforce/UninstallPackaged.py:21-24 defaults the
'package' option to `project__package__name` only. The asymmetric fix
expected (matching InstallPackageVersion._init_options, which falls
back through `name_managed` -> `name` -> `namespace`) is to consult
`project__package__name_managed` first. Today the function never
consults `project__package__name_managed`, so deploy_packaging of a
managed package whose unmanaged display name differs ends up
uninstalling the wrong package.

This test asserts the override source mentions `name_managed`; on dev
it does not, so the assertion fails -> XFAIL.
"""

import inspect

import pytest

from cumulusci.tasks.salesforce.UninstallPackaged import UninstallPackaged


@pytest.mark.xfail(
    reason="repro for #808 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_808():
    src = inspect.getsource(UninstallPackaged._init_options)
    assert "name_managed" in src, (
        "UninstallPackaged._init_options still falls back to "
        "project__package__name only; expected name_managed fallback. "
        f"Current source:\n{src}"
    )
