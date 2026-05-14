# Fix sketch — #3353: Enable Snowfakery task to use recipes from other repositories

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `bulkdata`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3353>

## Bug

Enable Snowfakery task to use recipes from other repositories

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

_See narrative for recommended action._

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3353.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3353:`).
