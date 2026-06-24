"""Repro for SFDO-Tooling/CumulusCI#710.

Projects today inherit four default scratch-org configurations from
``cumulusci/cumulusci.yml`` (``dev``, ``qa``, ``feature``, ``beta``,
``release``). The issue requests that a project be able to disable any
of these defaults via its own ``cumulusci.yml``, e.g.::

    orgs:
      scratch:
        dev:
          config_file: None

On ``origin/dev`` this is not honoured:

* ``cumulusci.core.utils.merge_config`` silently drops a ``None``
  override (``dictmerge`` skips ``None`` values), so the universal
  ``config_file: orgs/dev.json`` survives the merge.
* ``BaseProjectKeychain._load_scratch_orgs`` iterates every key under
  ``orgs.scratch`` and unconditionally calls ``create_scratch_org``.

Both behaviours are exercised below so the test fails (XFAIL) today
and passes once #710 is implemented in whichever direction the team
chooses (sentinel ``config_file: None``, an explicit ``disabled: true``
flag, omission of inherited keys, etc.) - the assertions only check
the externally-visible end state: ``dev`` is not in the keychain after
the project disables it.
"""

import pytest

from cumulusci.core.config import BaseProjectConfig, UniversalConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.utils import merge_config


@pytest.fixture()
def disabling_project_config():
    universal_config = UniversalConfig()
    merged = merge_config(
        {
            "universal_config": universal_config.config,
            "project_config": {
                "project": {"name": "TestProject"},
                "orgs": {"scratch": {"dev": {"config_file": None}}},
            },
        }
    )
    project_config = BaseProjectConfig(universal_config, config={"no_yaml": True})
    project_config.config = merged
    project_config.project__name = "TestProject"
    return project_config


@pytest.mark.xfail(
    reason="repro for #710 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_project_can_disable_default_dev_scratch_org_via_none_config_file(
    disabling_project_config,
):
    keychain = BaseProjectKeychain(disabling_project_config, key="0123456789123456")
    assert "dev" not in keychain.orgs, (
        "Setting `config_file: None` on the inherited `dev` scratch org config "
        "should disable it, but the keychain still loaded it."
    )


@pytest.mark.xfail(
    reason="repro for #710 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_merge_config_preserves_explicit_none_override():
    universal_config = UniversalConfig()
    merged = merge_config(
        {
            "universal_config": universal_config.config,
            "project_config": {
                "orgs": {"scratch": {"dev": {"config_file": None}}},
            },
        }
    )
    assert merged["orgs"]["scratch"]["dev"]["config_file"] is None, (
        "merge_config should preserve an explicit None override so that "
        "downstream code can detect a disabled scratch org config."
    )
