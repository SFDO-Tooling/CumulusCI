"""Regression repro for #3429.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``BaseProjectConfig.config_filename`` is hardcoded to
``"cumulusci.yml"`` (cumulusci/core/config/project_config.py:82) and
there is no environment variable (``CUMULUSCI_YML`` /
``CUMULUSCI_EXTRA_YAML``) or CLI flag (``--extra-yaml`` /
``--config-file``) to point at an alternate / additional YAML.

PR #3969 (branch ``extra-yaml-cli-flag``) is in flight and adds
``--extra-yaml`` plus a ``CUMULUSCI_EXTRA_YAML`` env var, but it has not
been merged into v4.10.0 / dev yet.

This test asserts the project_config module source references either
``CUMULUSCI_YML`` or ``CUMULUSCI_EXTRA_YAML`` (env-var override) or
exposes some helper such as ``resolve_extra_yaml``; on dev it fails
because none of those are present yet.
"""

import inspect

import pytest

import cumulusci.core.config.project_config as project_config_mod


@pytest.mark.xfail(
    reason="repro for #3429 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3429():
    src = inspect.getsource(project_config_mod)
    tokens = (
        "CUMULUSCI_YML",
        "CUMULUSCI_EXTRA_YAML",
        "resolve_extra_yaml",
        "--extra-yaml",
        "--config-file",
    )
    found = [t for t in tokens if t in src]
    assert found, (
        "cumulusci.core.config.project_config still has no env-var or helper "
        f"for an external/extra cumulusci.yml override (looked for {tokens}); "
        "config_filename is hardcoded to 'cumulusci.yml' (see #3429)"
    )
