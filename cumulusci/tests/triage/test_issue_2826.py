"""Regression repro for #2826.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: PackageXmlGenerator.parse_types
(cumulusci/tasks/metadata/package.py:105-117) calls
``os.listdir(self.directory)`` with no existence check. When
``deploy_unmanaged`` runs against a repo with no ``src/`` directory
(the original 2021 ask was that this flow silently no-op in that case),
``UpdatePackageXml`` raises a raw ``FileNotFoundError`` instead.

The fix is to either (a) guard ``parse_types`` so a missing directory
yields an empty package.xml, or (b) skip the task at the flow level via
a ``when:`` guard. Either way, the task should no longer surface a
``FileNotFoundError`` to the user.
"""

import os
import tempfile

import pytest

from cumulusci.tasks.metadata.package import PackageXmlGenerator


@pytest.mark.xfail(
    reason="repro for #2826 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_2826():
    with tempfile.TemporaryDirectory() as tmp:
        missing = os.path.join(tmp, "src")
        gen = PackageXmlGenerator(directory=missing, api_version="58.0")

        raised = None
        try:
            gen()
        except BaseException as e:
            raised = e

        assert not isinstance(raised, FileNotFoundError), (
            "PackageXmlGenerator still raises raw FileNotFoundError on a missing "
            "directory; deploy_unmanaged should silently no-op (or surface a typed "
            f"CumulusCIException instead). Got: {raised!r}"
        )
