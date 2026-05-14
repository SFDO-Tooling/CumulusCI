"""Regression repro for #3754.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``cumulusci/cli/utils.py``:

- ``get_latest_final_version`` (lines 65-79) hardcodes
  ``https://pypi.org/pypi/cumulusci/json``. There is no env-var or
  kwarg to point it at a private index or to disable the call.
- ``check_latest_version`` (lines 82-101) has no opt-out flag; the
  only workaround documented in the thread is to touch
  ``~/.cumulusci/cumulus_timestamp`` to a far-future epoch so the
  hourly check is skipped indefinitely.

This is painful for offline/air-gapped environments and for users on
corporate networks that block pypi.

The fix is to add an env var (e.g. ``CUMULUSCI_DISABLE_VERSION_CHECK``
and/or ``CUMULUSCI_PYPI_URL``) consumed inside ``check_latest_version``
/ ``get_latest_final_version``.

This test asserts ``cli.utils`` references one of those env vars or an
explicit disable/skip path; on dev it fails because none of them exist.
"""

import inspect

import pytest

import cumulusci.cli.utils as cli_utils


@pytest.mark.xfail(
    reason="repro for #3754 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3754():
    src = inspect.getsource(cli_utils)
    tokens = (
        "CUMULUSCI_DISABLE_VERSION_CHECK",
        "CUMULUSCI_PYPI_URL",
        "DISABLE_VERSION_CHECK",
        "PYPI_URL",
        "PYPI_INDEX",
    )
    found = [t for t in tokens if t in src]
    assert found, (
        "cumulusci.cli.utils still hardcodes https://pypi.org/pypi/cumulusci/json "
        "and offers no env-var to disable or redirect the version check (looked "
        f"for {tokens}); offline/air-gapped users have no clean opt-out (see #3754)"
    )
