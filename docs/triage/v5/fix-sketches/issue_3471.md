# Fix sketch — #3471: `Merged 0 commits into branch:` message displays when a non-Source Code change is

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `ci-integration`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3471>

## Bug

The reported log message originates from `_merge`: The log line at 251 reports `compare.behind_by` from github3's CompareCommits. `behind_by` is computed from the GitHub compare-commits endpoint and reflects how many commits the destination branch is behind the merged commit _as of the comparison's chosen merge-base_; for "effectively no-op" content merges (e.g. README/test.txt scenarios where dow...

## Target

`cumulusci/tasks/github/merge.py` lines 241-262

## Recommended approach (from triage narrative)

-   pass1: `keep-open` — small, well-localized fix (replace `compare.behind_by` with `len(list(compare.commits))` or report the SHA returned from `self.repo.merge(...)`); add a test covering the `behind_by=0` case.
-   pass2 labels: `bug, github, merge, low-priority`

---

<!-- subagent 12 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3471.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3471:`).
