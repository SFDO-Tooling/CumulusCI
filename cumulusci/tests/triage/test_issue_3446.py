"""Regression repro for #3446.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `BaseSalesforcePushTask._parse_version` in
cumulusci/tasks/push/tasks.py:26-33 unconditionally calls
`version.split(".")`. When the user runs `cci task run push_qa`
with only `--metadata_package_id` (no `--version` /
`--version_id`), `version` is `None` and the call raises
``AttributeError: 'NoneType' object has no attribute 'split'``
- the exact gist linked in the bug report.

This test calls `_parse_version(None)` and asserts it raises a
user-friendly TaskOptionsError instead of a bare AttributeError.
On dev it raises AttributeError -> XFAIL.
"""

import pytest

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.push.tasks import BaseSalesforcePushTask


@pytest.mark.xfail(
    reason="repro for #3446 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3446():
    # Bypass __init__ since BaseSalesforcePushTask needs an org/project
    # config; _parse_version only touches the supplied argument.
    task = BaseSalesforcePushTask.__new__(BaseSalesforcePushTask)
    with pytest.raises(TaskOptionsError):
        task._parse_version(None)
