# Fix sketch - #3746: Deleted Versions used for determining next version

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `packaging`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3746>

## Bug

Deleted Versions used for determining next version

## Target

`cumulusci/tasks/create_package_version.py` lines 529-545

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

`cumulusci/tests/triage/test_issue_3746.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3746:`).
