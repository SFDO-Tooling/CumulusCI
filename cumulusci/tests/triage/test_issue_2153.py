"""Regression repro for #2153.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `MergeBranch._create_conflict_pull_request`
(cumulusci/tasks/github/merge.py:264-288) only calls
`self.repo.create_pull(...)` to open the auto-generated
"Merge <source> into <branch>" PR. The original 2020 ask is to
also drop a comment on the source/child PR which tags the branch
subscribers so they get notified about the conflict.

A repo-wide search for `create_comment`/`issue_comment` returns
only test-fixture hits - production GitHub task code never
opens a PR/issue comment as part of this conflict path.

This test asserts that the merge task surface mentions a
comment-posting call. On dev it doesn't, so the assertion fails
-> XFAIL.
"""

import inspect

import pytest

from cumulusci.tasks.github.merge import MergeBranch


@pytest.mark.xfail(
    reason="repro for #2153 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_2153():
    src = inspect.getsource(MergeBranch)
    posts_comment = any(
        token in src
        for token in (
            "create_comment",
            "issue_comment",
            "post_comment",
        )
    )
    assert posts_comment, (
        "MergeBranch still only opens an auto-merge PR on conflict; "
        "no comment-on-original-PR path found to notify branch "
        "subscribers (see #2153)."
    )
