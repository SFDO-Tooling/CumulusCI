# Fix sketch — #2140: Prompt Org Configs when Org Does Not Exist and Command Runs Against It

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/2140>

## Bug

`keychain.get_org` raises `OrgNotFound` -> `cli/org.py:530-531` shows `"Org {name} does not exist in the keychain"`. No interactive prompt offering available scratch configs.

## Target

`cumulusci/cli/runtime.py` lines 95-104

## Recommended approach (from triage narrative)

-   pass1: `closed:stale-24mo` — 5yr `cli-usability` enhancement with no traction.
-   pass2 labels: `enhancement,cli-usability,stale`

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

`cumulusci/tests/triage/test_issue_2140.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #2140:`).
