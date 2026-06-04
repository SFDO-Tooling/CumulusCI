# Fix sketch - #2325: Task to turn off validation rules to allow data insert

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `bulkdata`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/2325>

## Bug

-   Trigger analog: `disable_tdtm_trigger_handlers` / `restore_tdtm_trigger_handlers` (`cumulusci.yml:738-747`). - DuplicateRule analog: `set_duplicate_rule_status` → `cumulusci.tasks.metadata_etl.duplicate_rules.SetDuplicateRuleStatus` (a 25-line `MetadataSingleEntityTransformTask` subclass with `entity = "DuplicateRule"`). - ValidationRule equivalent: **none.** `cci task list | grep -i -E "v...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` - feature still missing, clear implementation pattern, modest scope.

-   pass2 labels: `enhancement, bulkdata, metadata_etl, good-first-issue`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_2325.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #2325:`).
