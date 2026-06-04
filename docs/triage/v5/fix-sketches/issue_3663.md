# Fix sketch - #3663: When clause | Ability to pass in prior task response values

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `cli`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3663>

## Bug

-   `cumulusci/core/flowrunner.py:510-516` - the `when` Jinja context is hardcoded to `{"project_config": ..., "org_config": ...}`. Prior step results (`self.results`) are not exposed. - The `^^task.return_value` resolver lives elsewhere (option resolution path) and is not threaded into the `when` evaluator.

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` - natural extension of `when`; complements #3506.

-   pass2 labels: `enhancement, area:flows`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3663.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3663:`).
