"""Regression repro for #3471.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery; reverified on
origin/dev@1925a3083 - only ruff refactor since v4.10.0).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/github/merge.py `_merge` (L241-262) logs
"Merged {compare.behind_by} commits into branch: {branch_name}".
`compare.behind_by` comes from github3's CompareCommits which surfaces
GitHub's compare-com API; for effectively no-op content merges
(e.g. README/test.txt where downstream content already matches via
merge-base) the API returns 0, even though `self.repo.merge(...)` at
L249 just shipped a real merge commit. The "Merged 0 commits"
message is therefore confusing to users monitoring the auto-merge
output.

A real fix is to report either the SHA returned from
`self.repo.merge(...)` or `len(list(compare.commits))` instead of
`compare.behind_by`.

This test asserts the misleading `compare.behind_by` reference is
absent from merge.py. On dev it is still present at L251, so the
assertion fails -> XFAIL.
"""

from pathlib import Path

import pytest

import cumulusci


@pytest.mark.xfail(
    reason="repro for #3471 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3471():
    merge_path = Path(cumulusci.__file__).parent / "tasks" / "github" / "merge.py"
    text = merge_path.read_text()
    assert "compare.behind_by" not in text, (
        "Expected merge.py to no longer report `compare.behind_by` in the "
        "'Merged N commits into branch' log line (use compare.commits or the "
        "merge SHA instead); the misleading reference is still present."
    )
