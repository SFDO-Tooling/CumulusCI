"""Regression repro for #3604.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: there is no CCI task that writes computed dependencies
into a project's `sfdx-project.json`. Per the narrative:

> `uv run cci task list` returns 0 tasks that write `sfdx-project.json`.
> A project-wide grep for `unpackagedMetadata` returns no matches.

The maintainer filed an internal tracking ticket in 2023 but no implementation has
shipped through v4.10.0.

The fix is to add a new task (e.g. `update_sfdx_project_dependencies`)
that resolves the current cumulusci dependencies and writes them
into `sfdx-project.json` - likely populating the `unpackagedMetadata`
key (or `dependencies`).

This test scans cumulusci/tasks/ source for references to the
`unpackagedMetadata` key, which is the canonical sfdx-project.json
field for dependency tracking. On dev there are zero references, so
the assertion fails -> XFAIL.
"""

import pathlib

import pytest

import cumulusci as _cci_pkg


@pytest.mark.xfail(
    reason="repro for #3604 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3604():
    pkg_root = pathlib.Path(_cci_pkg.__file__).parent
    tasks_dir = pkg_root / "tasks"
    hits = []
    for py in tasks_dir.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "unpackagedMetadata" in text:
            hits.append(str(py.relative_to(pkg_root)))

    assert hits, (
        "No task under cumulusci/tasks/ references the sfdx-project.json "
        "'unpackagedMetadata' key; no task writes computed cumulusci "
        "dependencies back into sfdx-project.json. "
        f"Scanned {tasks_dir}; hits: {hits}"
    )
