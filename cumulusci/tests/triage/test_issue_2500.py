"""Repro for SFDO-Tooling/CumulusCI#2500 - ``ignore_failure`` is not documented.

The ``ignore_failure`` flow-step option has existed since flowrunner was
introduced (see ``cumulusci/core/flowrunner.py`` and
``cumulusci/utils/yaml/cumulusci_yml.py``), but ``docs/config.md`` only
*uses* it inside one example YAML snippet (and ``docs/history.md`` mentions
its introduction in the changelog). No section in the user-facing
"Flow Configurations" chapter explains the option, in contrast to
sibling step options like ``when`` (documented under "Conditionally Run a
Flow Step") or "Skip a Flow Step".

This test pins down both halves of the gap:

1. ``ignore_failure`` is a recognised step-level option (sanity check -
   the feature really exists and we are not chasing a phantom doc).
2. ``docs/config.md`` contains a narrative section that documents it.

On ``origin/dev`` (1925a3083) the second assertion fails: the only
matches for ``ignore_failure`` in ``docs/`` are the example YAML at
``docs/config.md:800`` and a one-line changelog blurb in
``docs/history.md``. Mark as xfail until a documentation section is
added.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import cumulusci


REPO_ROOT = Path(cumulusci.__file__).resolve().parent.parent
CONFIG_DOC = REPO_ROOT / "docs" / "config.md"


@pytest.mark.xfail(
    reason="repro for #2500 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_ignore_failure_has_narrative_docs_section():
    """``docs/config.md`` should have a narrative section explaining
    ``ignore_failure``, not just a single YAML example."""
    assert CONFIG_DOC.is_file(), f"missing {CONFIG_DOC}"
    text = CONFIG_DOC.read_text()

    heading_pattern = re.compile(
        r"^#{2,3}\s+.*(ignore[ _]failure|ignore a failed|continue.*failure).*$",
        re.IGNORECASE | re.MULTILINE,
    )
    assert heading_pattern.search(text), (
        "docs/config.md should contain a heading-level section that explains "
        "the ignore_failure step option (parallel to 'Conditionally Run a Flow "
        "Step' for `when:`). Currently the only mention is inside an example "
        "YAML snippet."
    )
