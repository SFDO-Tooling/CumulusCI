"""Regression repro for #3758.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/cumulusci.yml `push_upgrade_org` flow
(L1161-1177) terminates with `flow: config_qa` as step 5.
Semantically a push-upgrade targets a managed-package UAT sandbox,
so the final step should be `flow: config_managed`, not
`config_qa`. The two flows currently expand to the same task list
(`deploy_post`, `update_admin_profile`, `load_sample_data`) so
behavior is equivalent today - but semantics drift over time and
the docs link customers to the wrong flow page.

A real fix is a one-line YAML change: `flow: config_qa` ->
`flow: config_managed`.

This test loads cumulusci.yml and asserts the final step of
`push_upgrade_org` is `config_managed`. On dev it is `config_qa`,
so the assertion fails -> XFAIL.
"""

from pathlib import Path

import pytest
import yaml

import cumulusci


@pytest.mark.xfail(
    reason="repro for #3758 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3758():
    cumulusci_yml = Path(cumulusci.__file__).parent / "cumulusci.yml"
    data = yaml.safe_load(cumulusci_yml.read_text())
    flow = data["flows"]["push_upgrade_org"]
    last_step_key = max(flow["steps"].keys(), key=lambda k: int(k))
    last_step = flow["steps"][last_step_key]
    assert last_step.get("flow") == "config_managed", (
        "Expected push_upgrade_org's final step to be `flow: config_managed` "
        f"(targets a managed-package UAT sandbox), not {last_step!r}."
    )
