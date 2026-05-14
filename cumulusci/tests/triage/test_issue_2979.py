"""Regression repro for #2979.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/cumulusci.yml `deploy` task definition still
hard-codes `path: src` for `cumulusci.tasks.salesforce.Deploy`. The
ask (with davisagli's 3-tier fallback design) is to consult the
`default` entry of `packageDirectories` in `sfdx-project.json` (the
existing helper `default_package_path` in
`cumulusci/core/config/project_config.py`) when no explicit `path`
is configured, falling back to `src` only when neither is set.

`default_package_path` exists but is consumed only by
`create_package_version.py:230`; the Deploy task is not wired into
it.

This test loads the bundled cumulusci.yml YAML, finds the `deploy`
task definition, and asserts that it does NOT hard-code `path: src`.
On dev the path is still hard-coded, so the assertion fails -> XFAIL.
"""

import pathlib

import pytest
import yaml

import cumulusci as _cci_pkg


@pytest.mark.xfail(
    reason="repro for #2979 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_2979():
    yml_path = pathlib.Path(_cci_pkg.__file__).parent / "cumulusci.yml"
    cfg = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
    deploy_options = cfg["tasks"]["deploy"]["options"]
    assert deploy_options.get("path") != "src", (
        "deploy task in cumulusci.yml still hard-codes path: src; "
        "expected fallback to default_package_path / sfdx packageDirectories. "
        f"Current options: {deploy_options!r}"
    )
