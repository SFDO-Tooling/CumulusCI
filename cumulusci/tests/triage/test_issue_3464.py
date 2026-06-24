"""Repro for SFDO-Tooling/CumulusCI#3464 - Provide concise documentation of
``cumulusci.yml`` ``project`` configuration options.

The user asked: "I would like ALL configuration tags and options defined,
with a brief description (even just one sentence) in
https://cumulusci.readthedocs.io/en/stable/config.html".

On ``origin/dev`` (1925a3083) ``cumulusci/utils/yaml/cumulusci_yml.py``
defines a ``Project`` Pydantic model with these top-level keys:

* ``name``
* ``package``
* ``test``
* ``git``
* ``dependencies``
* ``dependency_resolutions``
* ``dependency_pins``
* ``source_format``
* ``custom``

``docs/config.md`` shows ONE example YAML block (line ~281) using a subset
of these keys but has no reference subsection that names every supported
key. Several keys - notably ``dependency_resolutions``, ``dependency_pins``,
and ``source_format`` - never appear in ``docs/config.md`` at all (they
are buried in ``docs/dev.md``, which is exactly the "scattered" complaint
in the issue).

The xfail test asserts each ``Project`` field name appears at least once
in ``docs/config.md``. Today several keys are missing, so the assertion
fails. Once ``docs/config.md`` gets a "Project Configuration Reference"
section listing every key, the test will XPASS.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import cumulusci
from cumulusci.utils.yaml.cumulusci_yml import Project


REPO_ROOT = Path(cumulusci.__file__).resolve().parent.parent
CONFIG_DOC = REPO_ROOT / "docs" / "config.md"


@pytest.mark.xfail(
    reason="repro for #3464 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_every_project_key_is_mentioned_in_config_doc():
    """``docs/config.md`` should mention every top-level ``project:`` key
    defined by the ``Project`` Pydantic model. Today several keys are
    missing or only documented in other doc pages."""
    text = CONFIG_DOC.read_text()
    project_keys = sorted(Project.__fields__.keys())
    missing = [k for k in project_keys if k not in text]
    assert not missing, (
        f"docs/config.md does not mention these project-config keys: {missing}. "
        f"The full set declared in Project Pydantic model: {project_keys}."
    )
