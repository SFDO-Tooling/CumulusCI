# Fix sketch - #3849: urllib3 v2 breaks Robot tests on a fresh pip install

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `python-modernization`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3849>

## Bug

urllib3 v2 breaks Robot tests on a fresh pip install

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

`cumulusci/tests/triage/test_issue_3849.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3849:`).
