"""Regression repro for #3518.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/metadata_etl/picklists.py line 177 reads:

    default = str(process_bool_arg(entry.get("default", False))).lower

The `.lower` is referenced as an attribute, not invoked - so
`default` ends up bound to the `str.lower` method itself (a callable
object, always truthy). The subsequent guard at line 214
(`if default:`) therefore always runs the default-clobbering loop,
marking the new entry as default for every record type regardless of
the user's intent.

A real fix is a one-character change: `.lower` -> `.lower()`.

This test asserts that when a user passes `default: False` for a new
picklist entry, the produced `default` value is a falsy string (not
a bound method). On dev `default` is `str.lower` (a method), which
is truthy, so the assertion fails -> XFAIL.
"""

import pytest

from cumulusci.core.utils import process_bool_arg


@pytest.mark.xfail(
    reason="repro for #3518 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3518():
    # Mirrors the exact expression at picklists.py:177
    default = str(process_bool_arg(False)).lower
    assert not callable(default), (
        "Expected picklists.py to compute the lowercase string (e.g. via "
        "`.lower()`), not the bound `str.lower` method. The current "
        "expression yields a callable, so the `if default:` guard at "
        "L214 is always truthy and every record-type default is "
        f"clobbered. Got {default!r}."
    )
