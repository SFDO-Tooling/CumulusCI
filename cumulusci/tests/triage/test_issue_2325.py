"""Regression repro for #2325.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: CumulusCI ships ``disable_tdtm_trigger_handlers`` /
``restore_tdtm_trigger_handlers`` (cumulusci.yml:738-747) for triggers
and ``set_duplicate_rule_status`` for DuplicateRule, but offers no
analogous task for toggling Salesforce ValidationRules around a data
load. The user requested an OOTB ``set_validation_rule_status`` /
``disable_validation_rules`` task; ``cci task list | grep -i validation``
returns only the duplicate-rule task on v4.10.0.

The fix is to add a ``MetadataSingleEntityTransformTask`` subclass for
``entity = "ValidationRule"`` and wire it into ``cumulusci.yml`` with
both disable/restore (or set-status) flavours, mirroring the existing
TDTM/DuplicateRule pattern.

This test asserts ``cumulusci.yml`` declares at least one validation-rule
toggle task; on dev it fails because no such task exists.
"""

from pathlib import Path

import pytest
import yaml

import cumulusci


@pytest.mark.xfail(
    reason="repro for #2325 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_2325():
    cci_root = Path(cumulusci.__file__).parent
    with open(cci_root / "cumulusci.yml") as f:
        data = yaml.safe_load(f)

    task_names = set(data.get("tasks", {}).keys())
    candidates = {
        "set_validation_rule_status",
        "disable_validation_rules",
        "restore_validation_rules",
        "activate_validation_rules",
        "deactivate_validation_rules",
    }
    intersection = task_names & candidates
    assert intersection, (
        "cumulusci.yml still ships no ValidationRule toggle task. Expected one "
        f"of {sorted(candidates)} to mirror the disable_tdtm_trigger_handlers / "
        "set_duplicate_rule_status pattern (see #2325)"
    )
