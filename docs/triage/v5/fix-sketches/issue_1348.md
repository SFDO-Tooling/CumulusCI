# Fix sketch - #1348: Multiple Git Provider Support

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `cli`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/1348>

## Bug

`rg -li "gitlab" cumulusci/` and `rg -li "bitbucket" cumulusci/` both return zero matches. The `ci_feature` flow still hardcodes GitHub-specific tasks:

## Target

`cumulusci/cumulusci.yml` lines 767-789

## Recommended approach (from triage narrative)

-   pass1: `closed:stale-24mo` - large architectural change (multi-VCS abstraction); 6yr no traction; user `zenibako` confirmed using cci on GitLab via custom flows is feasible.

-   pass2 labels: `enhancement,stale,wontfix-candidate`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_1348.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #1348:`).
