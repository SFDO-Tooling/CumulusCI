"""Regression repro for #3440.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/core/config/project_config.py:514-523
`default_package_path` is the simple "first packageDirectory with
`default: true`" pattern; falls back to `force-app`, then `src`. It
takes no arguments, offers no name-based lookup for multi-package
sfdx-project.json layouts, emits no multi-package warnings, and does
not hard-fail when both `default` and `force-app` are missing.

A real fix likely either (a) refactors `default_package_path` into a
method accepting a package name, or (b) adds a sibling method
(`package_path(name)` / `get_package_directory(name)`) that supports
name-based lookup.

This test asserts that `BaseProjectConfig` exposes some way to look
up package directories by name for multi-package projects. On dev no
such API exists, so the assertion fails -> XFAIL.
"""

import pytest

from cumulusci.core.config.project_config import BaseProjectConfig


@pytest.mark.xfail(
    reason="repro for #3440 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3440():
    candidate_attrs = (
        "package_path",
        "get_package_directory",
        "get_package_path",
        "package_directory_for_name",
    )
    found = [a for a in candidate_attrs if hasattr(BaseProjectConfig, a)]
    assert found, (
        "Expected BaseProjectConfig to expose a name-based package-directory "
        f"lookup API (one of {candidate_attrs!r}) for multi-package sfdx "
        "projects; none present."
    )
