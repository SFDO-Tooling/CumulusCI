"""Repro for CumulusCI issue #3541 — scratch org alias becomes ``None__<org>``.

When :pyfunc:`BaseProjectKeychain.create_scratch_org` builds the SFDX alias it
does::

    scratch_config["sfdx_alias"] = (
        f"{self.project_config.project__name}__{org_name}"
    )

If ``project__name`` evaluates to ``None`` (no ``project.name`` in the loaded
config, or the project hasn't fully resolved yet — e.g. during the eager
``_load_scratch_orgs`` pass on keychain construction) the resulting alias is
the literal string ``"None__<org>"``.  That string is then passed to
``sfdx force config set target-org=None__dev`` which is exactly what
the reporter (and at least one other commenter) saw.

Correct behaviour: either fall back to ``org_name`` alone or raise a clear
CumulusCIException — *never* embed the literal Python repr of ``None`` in a
shell argument.

No scratch org / network required.
"""

from __future__ import annotations

import pytest

from cumulusci.core.config import BaseProjectConfig, UniversalConfig
from cumulusci.core.keychain import BaseProjectKeychain


@pytest.mark.xfail(
    reason=("repro for #3541 — see docs/triage/v5/repro-results.md"),
    strict=False,
)
def test_create_scratch_org_without_project_name_does_not_yield_None_alias():
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(
        universal_config,
        {"orgs": {"scratch": {"dev": {}}}},
    )
    assert project_config.project__name is None, (
        "precondition: this repro models a project config where project.name "
        "is unset, matching the reporter's symptom"
    )

    keychain = BaseProjectKeychain(project_config, key=None)
    keychain.create_scratch_org("dev", "dev")
    alias = keychain.get_org("dev").config["sfdx_alias"]

    assert "None" not in alias.split("__"), (
        f"sfdx_alias is {alias!r} — literal 'None' should never appear in a "
        "shell-bound SFDX alias. Expected fallback to 'dev' or a raised "
        "CumulusCIException."
    )


@pytest.mark.xfail(
    reason=("repro for #3541 — see docs/triage/v5/repro-results.md"),
    strict=False,
)
def test_load_scratch_orgs_on_keychain_init_does_not_yield_None_alias():
    """During keychain construction ``_load_scratch_orgs`` eagerly invokes
    ``create_scratch_org`` for every scratch config in cumulusci.yml.  If
    project.name resolves to None at that moment, every eagerly-created org
    inherits a ``None__<config>`` alias — and the user only notices when
    ``cci org info dev`` finally runs sfdx with target-org=None__dev."""
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(
        universal_config,
        {"orgs": {"scratch": {"dev": {}, "qa": {}}}},
    )
    keychain = BaseProjectKeychain(project_config, key=None)

    bad = {
        name: keychain.get_org(name).config["sfdx_alias"]
        for name in ("dev", "qa")
        if "None" in keychain.get_org(name).config["sfdx_alias"].split("__")
    }
    assert not bad, (
        f"Eagerly-loaded scratch orgs produced None__-prefixed aliases: {bad!r}"
    )
