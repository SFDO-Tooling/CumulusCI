# Fix sketch - #3446: CCI task push_qa crashes for Unlocked package with no namespace

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `packaging`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3446>

## Bug

-   `cumulusci/tasks/push/tasks.py:33` - `version_parts = version.split(".")` (no None-guard above). - `cumulusci/tasks/push/tasks.py:283-297` - `_run_task` does not validate `version` before calling `_get_version`. - Test: `_(repro evidence; see narrative)_` passes on v4.10.0.

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` - real bug, simple fix.

-   pass2 labels: `bug`, `good-first-issue`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3446.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3446:`).
