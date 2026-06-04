# Fix sketch - #3773: retrieve_profile task seems to be missing some Metadata

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `metadata-etl`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3773>

## Bug

-   `cumulusci/salesforce_api/retrieve_profile_api.py:164-195` - no `FieldPermissions` query. - Greped `FieldPermission|field_permission|fieldPermission` - only the

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: keep-open - needs additional `FieldPermissions` query plus inclusion of those parent SObjectTypes in the `CustomObject` retrieve set.

-   pass2 labels: `severity:medium,area:retrieve-profile,type:bug`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3773.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3773:`).
