"""Regression repro for #3441.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/create_package_version.py
`_get_base_version_number` (lines 529-563 on v4.10.0) branches only
on `None` (default) and the literal `"latest_github_release"` sentinel;
any other string is parsed as a literal version number. There is no
`"default"` / `"highest"` sentinel and no support for resetting a
flow-overridden `version_base` back to the default behavior.

The fix (per the issue) is to add a sentinel string such as
`"default"` or `"highest"` that triggers the same SOQL-derived
highest-version lookup the default-None path uses.

This test inspects `_get_base_version_number` source and asserts that
the function handles a `"default"` (or `"highest"`) sentinel. On dev
it does not, so the assertion fails -> XFAIL.
"""

import inspect

import pytest

from cumulusci.tasks.create_package_version import CreatePackageVersion


@pytest.mark.xfail(
    reason="repro for #3441 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3441():
    src = inspect.getsource(CreatePackageVersion._get_base_version_number)
    has_default_sentinel = (
        '"default"' in src or "'default'" in src or '"highest"' in src
    )
    assert has_default_sentinel, (
        "_get_base_version_number does not handle a 'default'/'highest' sentinel "
        "for version_base; flow override cannot reset to default lookup. "
        f"Current source:\n{src}"
    )
