"""Regression repro for #1348.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: CumulusCI is GitHub-only. There are no `gitlab` or
`bitbucket` references in the `cumulusci/` package, and the
`ci_feature` flow still hardcodes GitHub-specific tasks
(`github_parent_pr_notes`, `github_automerge_feature`). The
2017 feature ask is to add a VCS abstraction so projects on
other providers can use CumulusCI.

This test loads the universal cumulusci.yml and asserts that
`ci_feature` does NOT step into any GitHub-specific task -
which it does today, so this fails -> XFAIL.
"""

import pytest

from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load
from pathlib import Path

import cumulusci


@pytest.mark.xfail(
    reason="repro for #1348 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_1348():
    universal_yaml = Path(cumulusci.__file__).resolve().parent / "cumulusci.yml"
    config = cci_safe_load(universal_yaml.open(), str(universal_yaml))
    flows = config.get("flows", {})
    ci_feature = flows.get("ci_feature") or {}
    steps = ci_feature.get("steps", {})
    step_text = " ".join(
        str(step.get("task") or step.get("flow") or "") for step in steps.values()
    )
    has_github_specific = (
        "github_parent_pr_notes" in step_text or "github_automerge_feature" in step_text
    )
    assert not has_github_specific, (
        "ci_feature still references GitHub-specific tasks; no VCS "
        "abstraction exposed for GitLab/Bitbucket users (see #1348)."
    )
