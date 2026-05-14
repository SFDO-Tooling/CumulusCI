"""Regression repro for #3543.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/dx_convert_from.py only exposes the
`extra` and `src_dir` task options. The issue asks for a
`load_sfdx_project_paths` (a.k.a. `resolve_sfdx_package_dirs`) option
that auto-discovers source directories from `sfdx-project.json` so
multi-package projects can convert all sources in one invocation.

This test imports `DxConvertFrom` and asserts that
`load_sfdx_project_paths` (or `resolve_sfdx_package_dirs`) is a
declared task option. On dev neither key is present, so the
assertion fails -> XFAIL.
"""

import pytest

from cumulusci.tasks.dx_convert_from import DxConvertFrom


@pytest.mark.xfail(
    reason="repro for #3543 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3543():
    options = DxConvertFrom.task_options
    has_option = (
        "load_sfdx_project_paths" in options or "resolve_sfdx_package_dirs" in options
    )
    assert has_option, (
        "DxConvertFrom is missing a load_sfdx_project_paths / "
        f"resolve_sfdx_package_dirs option. Current options: {list(options.keys())}"
    )
