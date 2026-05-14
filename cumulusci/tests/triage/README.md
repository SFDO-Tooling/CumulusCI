# `cumulusci/tests/triage/`

Regression-repro tests for open issues. Each test file targets one
issue.

## Conventions

-   File naming: `test_issue_<NNNN>.py` where `<NNNN>` is the GitHub
    issue number.
-   Every test in this directory uses `@pytest.mark.xfail(strict=False)`
    by default. The xfail marker captures the expected failure mode and
    is removed by the corresponding fix-PR.
-   `strict=False` is intentional: if a bug resolves independently (a
    different PR lands, an upstream dependency is fixed, etc.), the
    test will `XPASS` rather than fail CI. A harvest pass periodically
    converts `XPASS` issues to `NOT-REPRODUCED-on-dev` and either
    rewrites the test or drops it.
-   Tests MUST be fast (`< 2s`), import-only or mocked. No live
    Salesforce org, no real network, no scratch-org creation. Use
    `unittest.mock` / fixtures liberally.

## Lifecycle

1.  Triage subagent verifies a bug reproduces on `origin/dev`.
2.  Subagent writes `test_issue_<NNNN>.py` with `@pytest.mark.xfail` +
    a code-level assertion that captures the bug.
3.  Test is committed to this directory via the triage umbrella PR.
4.  When the bug is fixed:
    -   Fix-PR removes the `@pytest.mark.xfail` marker.
    -   Fix-PR confirms the test now passes.
    -   Fix-PR moves the test out of this directory to its natural
        home (e.g. `cumulusci/tasks/<module>/tests/`) — or leaves it
        here with the marker removed, whichever is cleaner.

## See also

-   `docs/triage/v5/repro-results.md` — narrative evidence per issue.
-   `docs/triage/v5/fix-sketches/issue_<NNNN>.md` — proposed fix
    approach per issue.
-   `docs/triage/v5/proposals.md` — pass-1 classification matrix.

## Running

```bash
uv run pytest cumulusci/tests/triage/ -v
```

Expected outcome: every test reports `XFAIL`. If any reports `XPASS`,
that is signal that a bug resolved independently — see the harvest
xpass list in `docs/triage/v5/` (if present).
