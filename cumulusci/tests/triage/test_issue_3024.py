"""Regression repro for #3024.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: The order of ``group:`` values in
``cumulusci/cumulusci.yml`` still has "Metadata Transformations" first
and buries "Continuous Integration" near the bottom (~position 20+ in
the first-appearance ordering). The user-requested "Org Setup" group
does not exist (the closest is "Setup"). This means the VS Code
extension that drives off ``group:`` shows tasks in the same
not-very-useful order CumulusCI ships them in.

The fix is either to (a) reorder the canonical YAML so the most
commonly used groups (Continuous Integration, Setup) appear toward
the top, or (b) introduce an explicit ``group_order:`` list in the
project schema and have the extension consume that.

This test asserts "Continuous Integration" appears in the first half
of the unique groups (by first appearance). On dev it fails because
it currently appears ~last.
"""

from pathlib import Path

import pytest
import yaml

import cumulusci


@pytest.mark.xfail(
    reason="repro for #3024 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3024():
    cci_root = Path(cumulusci.__file__).parent
    with open(cci_root / "cumulusci.yml") as f:
        data = yaml.safe_load(f)

    seen = []
    for _, task in data.get("tasks", {}).items():
        group = task.get("group")
        if group and group not in seen:
            seen.append(group)

    assert "Continuous Integration" in seen, (
        "'Continuous Integration' group missing from cumulusci.yml — test needs updating"
    )
    ci_pos = seen.index("Continuous Integration")
    halfway = len(seen) // 2
    assert ci_pos < halfway, (
        f"'Continuous Integration' still appears at position {ci_pos + 1} of "
        f"{len(seen)} groups (>= halfway {halfway + 1}); cumulusci.yml has not "
        f"been reordered to surface common groups first (see #3024). Order: {seen}"
    )
