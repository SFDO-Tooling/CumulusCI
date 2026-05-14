"""Regression repro for #3137.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/metadata/package.py CustomObjectParser
(L441-459) hard-skips any object file whose name does not end in
`__c.object`, `__mdt.object`, `__e.object`, or `__b.object`. This is
a managed-package-world holdover that excludes Case (and every other
standard SObject with a sidecar `.object` containing custom fields)
from the generated package.xml. UpdatePackageXml does not expose an
opt-in option (e.g. `include_standard_objects=True`) for the user to
override.

A real fix exposes either a task option (`include_standard_objects`)
or makes the parser configurable so users who genuinely want a
standard Case object listed can do so without monkey-patching.

This test parses a fake `objects/` folder containing `Case.object`
(a standard object) and asserts the generated members include
`Case`. On dev `Case` is filtered out, so the assertion fails ->
XFAIL.
"""

import pytest

from cumulusci.tasks.metadata.package import CustomObjectParser


@pytest.mark.xfail(
    reason="repro for #3137 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3137():
    parser = CustomObjectParser.__new__(CustomObjectParser)
    members = parser._parse_item("Case.object")
    assert members == ["Case"], (
        "Expected CustomObjectParser to include standard 'Case' object in "
        f"package.xml members (or expose an opt-in option); got {members!r}."
    )
