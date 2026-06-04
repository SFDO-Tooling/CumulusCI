# Fix sketch - #1432: CCI Inconsistencies in validating arguments

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `cli`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/1432>

## Bug

Old-style `task_options` dict still does not validate unknown keys: Repro test passes (= unknown `colour` typo is silently accepted via YAML/Python path): Test path: `_(repro evidence; see narrative)_`.

## Target

`cumulusci/core/tasks.py` lines 186-196

## Recommended approach (from triage narrative)

-   pass1: `closed:stale-24mo` - 5yr; partial mitigation in place; full fix would require reworking every legacy `task_options` dict task.

-   pass2 labels: `bug,stale,partially-fixed`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_1432.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #1432:`).
