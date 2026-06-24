"""Regression repro for #3721.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause:
- cumulusci/tasks/create_package_version.py:184 defaults
  `version_name` to the literal string `"Release"`.
- cumulusci/cumulusci.yml `upload_production` task hard-codes
  `name: Release`.

The issue asks for the default to be the predicted version number
(or a jinja2 template that resolves to it), so consumers do not all
end up with a homogeneous `"Release"` name. The fix has shipped on
the muselab-d2x fork (commit 7aaf348f3) but is not in upstream cci.

This test inspects the source of `create_package_version.py` and
asserts that the literal `or "Release"` fallback has been removed.
On dev it is still present, so the assertion fails -> XFAIL.
"""

import pathlib

import pytest

import cumulusci.tasks.create_package_version as _cpv_mod


@pytest.mark.xfail(
    reason="repro for #3721 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3721():
    src = pathlib.Path(_cpv_mod.__file__).read_text(encoding="utf-8")
    assert 'or "Release"' not in src, (
        "create_package_version.py still defaults version_name to literal "
        '"Release"; expected version-number-based default (jinja2 template '
        "or computed string)."
    )
