# Fix sketch — #2153: Add comment to original PR which tags all branch subscribers when a merge

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `ci-integration`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/2153>

## Bug

`cumulusci/tasks/github/merge.py` `_create_conflict_pull_request` (the only place an auto-merge PR is created): The method only creates the conflict PR; it never opens a comment on any PR (the original child PR or otherwise). Repo-wide grep for `create_comment|issue_comment|pr.create_comment|comment.*pull_request` under `cumulusci/tasks/github` returns no hits in production code (only test fixture...

## Target

`cumulusci/tasks/github/merge.py` lines 264-288

## Recommended approach (from triage narrative)

-   pass1: `keep-open` — small, well-scoped enhancement; reasonable "good-second-issue".
-   pass2 labels: `enhancement, github, merge-conflict`

---

<!-- subagent 9 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_2153.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #2153:`).
