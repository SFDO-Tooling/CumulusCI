# Fix sketch — #733: Prompt to delete scratch org when creating one that already exists

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/733>

## Bug

Behaviour identical to the 2018 report — hard error, no interactive Y/N prompt.

## Target

`cumulusci/cli/runtime.py` lines 126-140

## Recommended approach (from triage narrative)

-   pass1: `closed:stale-24mo` — 7-year-old `cli-usability` enhancement, no traction, original tracking W-028291.
-   pass2 labels: `enhancement,cli-usability,stale`

---

<!-- subagent 5 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_733.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #733:`).
