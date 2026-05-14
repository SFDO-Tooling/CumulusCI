"""Regression repro for #3307.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``cci project init`` (cumulusci/cli/project.py:37-41) only
renders Jinja templates from CumulusCI's bundled
``cumulusci/files/templates/project`` directory. There is no
``--template`` (or equivalent) CLI option to point the command at a
user-supplied template directory or git URL, so users cannot
bootstrap a project from an org-specific template.

The fix is to add a ``--template`` click option to ``project_init``
that accepts a path or git URL and renders that template instead of
(or in addition to) the bundled one.

This test asserts ``project_init`` has a ``template``-named click
option; on dev it fails because no such option exists.
"""

import pytest

from cumulusci.cli.project import project_init


@pytest.mark.xfail(
    reason="repro for #3307 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3307():
    param_names = {p.name for p in project_init.params}
    template_opts = {n for n in param_names if "template" in n.lower()}
    assert template_opts, (
        "cci project init still has no --template CLI option; users cannot "
        f"point the command at a custom template directory or git URL. "
        f"Existing params: {sorted(param_names)} (see #3307)"
    )
