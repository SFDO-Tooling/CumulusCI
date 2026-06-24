"""Regression repro for #3331.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/metadata/metadata_map.yml line 45-48
maps the `assignmentRules` folder to MDAPI type
`AssignmentRule` (singular). Salesforce Metadata API expects
`AssignmentRules` (plural) - see the analogous `autoResponseRules`
key (lines 60-63) which is already correctly `AutoResponseRules`.

Running `update_package_xml` against a project with
`assignmentRules/Case.assignmentRules` emits
`<name>AssignmentRule</name>` and the deploy then fails with
"INVALID_TYPE: AssignmentRule is not a valid metadata type".

A real fix is a single-line YAML change.

This test asserts the YAML maps `assignmentRules` to the plural
`AssignmentRules`. On dev the mapping is still singular, so the
assertion fails -> XFAIL.
"""

from pathlib import Path

import pytest
import yaml

import cumulusci


@pytest.mark.xfail(
    reason="repro for #3331 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3331():
    metadata_map_path = (
        Path(cumulusci.__file__).parent / "tasks" / "metadata" / "metadata_map.yml"
    )
    metadata_map = yaml.safe_load(metadata_map_path.read_text())
    entries = metadata_map.get("assignmentRules", [])
    types = [e.get("type") for e in entries]
    assert "AssignmentRules" in types, (
        "Expected metadata_map.yml `assignmentRules` folder to map to MDAPI "
        f"type 'AssignmentRules' (plural, matching MDAPI); got types {types!r}."
    )
