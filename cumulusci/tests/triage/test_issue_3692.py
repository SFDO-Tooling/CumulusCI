"""Regression repro for #3692.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/metadata/metadata_map.yml does not include
a `digitalExperiences` (or `digitalExperienceConfigs`) entry. The
`PackageXmlGenerator` therefore raises
`MetadataParserMissingError("No parser configuration found for
subdirectory %s")` on any Enhanced LWR site, which corresponds
directly to the user's reported error.

The fix is to add `digitalExperiences` (and likely
`digitalExperienceConfigs`) entries to `metadata_map.yml` with a
suitable bundle parser class.

This test loads metadata_map.yml and asserts that the
`digitalExperiences` key is present. On dev it is absent, so the
assertion fails -> XFAIL.
"""

import pathlib

import pytest
import yaml

import cumulusci.tasks.metadata as _md_pkg


@pytest.mark.xfail(
    reason="repro for #3692 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3692():
    map_path = pathlib.Path(_md_pkg.__file__).parent / "metadata_map.yml"
    cfg = yaml.safe_load(map_path.read_text(encoding="utf-8"))
    assert "digitalExperiences" in cfg, (
        "metadata_map.yml is missing a digitalExperiences entry; "
        "Enhanced LWR sites fail with MetadataParserMissingError. "
        f"Present keys (first 30): {sorted(cfg.keys())[:30]}"
    )
