"""Regression repro for #733.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: CliRuntime.check_org_overwrite() at cumulusci/cli/runtime.py
hardcodes a `click.ClickException` for an already-created scratch org.
The original 2018 ask is to interactively prompt the user (Y/N) to delete
the existing scratch org rather than hard-erroring.

The fix would introduce `click.confirm` / `click.prompt` (or equivalent) so
the function offers an interactive choice. This test asserts presence of a
prompt mechanism inside `check_org_overwrite`; on dev it fails because the
function still only raises `ClickException`.
"""

import inspect

import pytest

from cumulusci.cli.runtime import CliRuntime


@pytest.mark.xfail(
    reason="repro for #733 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_733():
    src = inspect.getsource(CliRuntime.check_org_overwrite)
    has_prompt = any(token in src for token in ("click.confirm", "click.prompt"))
    assert has_prompt, (
        "check_org_overwrite still hard-errors with ClickException; "
        "no interactive prompt path found in source"
    )
