# Fix sketch — #3618: Allow for list when deleting/removing CumulusCI orgs

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3618>

## Bug

-   `cumulusci/cli/org.py:519-545` — `org_remove` decorated with `@orgname_option_or_argument(required=True)`, takes a single `org_name`. - `cumulusci/cli/org.py:605-625` — `org_scratch_delete` same pattern, single `org_name`. - No `nargs=-1`, no comma-split helper; passing `org1,org2` would be treated as a single literal alias and fail keychain lookup.

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` — legitimately useful for cleanup workflows; small implementation surface.
-   pass2 labels: `enhancement, area:cli, good-first-issue`

<!-- subagent 11 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3618.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3618:`).
