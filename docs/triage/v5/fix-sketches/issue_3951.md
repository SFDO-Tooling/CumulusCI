# Fix sketch - #3951: set_duplicate_rule_status broken

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `metadata-etl`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3951>

## Bug

set\*duplicate_rule_status broken

## Target

\_See narrative for target file:line.\*

## Recommended approach (from triage narrative)

-   pass1: `improve-error-message` - keep open.

-   pass2 labels: `bug`, `good-first-issue`, `documentation` **Notes**: Two improvements: 1. Update the `set_duplicate_rule_status` task option help to call out the `<Object>.<RuleName>` format requirement.

2. | Same as #3613 - improve the base.py:332 error to list the files actually retrieved. The `Cannot find metadata file` error is shared across most `MetadataSingleEntityTransformTask` subclasses, so a single base-class fix would benefit several issues at once. ---

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3951.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3951:`).
