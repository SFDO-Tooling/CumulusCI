"""Regression repro for #2140.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `CliRuntime.get_org()` in cumulusci/cli/runtime.py
hard-errors with `click.UsageError("No org specified and no
default org set.")` when the requested org does not exist in
the keychain (or `OrgNotFound` from `keychain.get_org()`
bubbles up to `cli/org.py` as a plain ClickException). The 2020
ask is to instead surface an interactive prompt that lets the
user pick from configured scratch org configs.

This test asserts that `get_org` source contains a prompt
mechanism (click.prompt / click.Choice / scratch-config-listing
helper). On dev it doesn't, so the assertion fails -> XFAIL.
"""

import inspect

import pytest

from cumulusci.cli.runtime import CliRuntime


@pytest.mark.xfail(
    reason="repro for #2140 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_2140():
    src = inspect.getsource(CliRuntime.get_org)
    has_prompt = any(
        token in src
        for token in (
            "click.prompt",
            "click.confirm",
            "click.Choice",
            "scratch_configs",
            "scratch configs",
        )
    )
    assert has_prompt, (
        "CliRuntime.get_org still hard-errors when no org is found; "
        "no interactive scratch-config picker (see #2140)."
    )
