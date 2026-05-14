# Fix sketch — #2402: Create a --rebuild-org parameter for cci flow run

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/2402>

## Bug

Only `--delete-org` exists. `rg -i "rebuild.org"` returns zero hits.

## Target

`cumulusci/cli/flow.py` lines 119-145

## Recommended approach (from triage narrative)

-   pass1: `closed:stale-24mo` — 5yr; tracked W-10502624 (no movement); user can accomplish via `cci org scratch_delete X && cci flow run`.
-   pass2 labels: `enhancement,stale`

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

`cumulusci/tests/triage/test_issue_2402.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #2402:`).
