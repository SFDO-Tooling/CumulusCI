"""Regression repro for #3603.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (partial; R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/core/source/github.py L126:
    self.commit = self.repo.ref(ref).object.sha
lets a raw github3 `NotFoundError("404 [No message]")` bubble out when
the user-specified ref / tag / branch on an _existing_ repo does not
resolve. The peer cases (repo-not-found at L1/2 and the `release:`
spec at L103) ARE wrapped in DependencyResolutionError with the URL
and ref context; only the ref-not-found case-3 path leaks.

A real fix wraps `self.repo.ref(ref)` in try/except NotFoundError and
re-raises DependencyResolutionError mentioning the repo URL and the
missing ref/tag/branch.

This test simulates a NotFoundError from `repo.ref()` and asserts the
resulting exception is a DependencyResolutionError (not a raw
NotFoundError) and includes the missing tag in its message. On dev
the raw NotFoundError leaks, so both assertions fail -> XFAIL.
"""

from unittest import mock

import pytest
from github3.exceptions import NotFoundError

from cumulusci.core.exceptions import DependencyResolutionError
from cumulusci.core.source.github import GitHubSource
from cumulusci.utils.yaml.cumulusci_yml import GitHubSourceModel


class _DummyResponse:
    status_code = 404
    content = ""


@pytest.mark.xfail(
    reason="repro for #3603 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3603():
    project_config = mock.Mock()
    spec = GitHubSourceModel(
        github="https://github.com/Test/Repo",
        tag="release/9.99.99-no-such-tag",
    )

    fake_repo = mock.Mock()
    fake_repo.ref.side_effect = lambda *_a, **_kw: (_ for _ in ()).throw(
        NotFoundError(_DummyResponse)
    )

    fake_gh = mock.Mock()
    with (
        mock.patch(
            "cumulusci.core.source.github.get_github_api_for_repo",
            return_value=fake_gh,
        ),
        mock.patch.object(GitHubSource, "_get_repository", return_value=fake_repo),
    ):
        with pytest.raises(DependencyResolutionError) as exc:
            GitHubSource(project_config, spec)
        msg = str(exc.value)
        assert "no-such-tag" in msg or "Test/Repo" in msg, (
            "Expected case-3 ref-not-found error to surface a "
            f"DependencyResolutionError mentioning the repo or ref; got: {msg!r}"
        )
