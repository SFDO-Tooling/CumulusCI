# Fix sketch - #3349: Make generated dataset recordType tables unique based on table instead of sf_object

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `bulkdata`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3349>

## Bug

Make generated dataset recordType tables unique based on table instead of sf\*object

## Target

\_See narrative for target file:line.\*

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

`cumulusci/tests/triage/test_issue_3349.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3349:`).
