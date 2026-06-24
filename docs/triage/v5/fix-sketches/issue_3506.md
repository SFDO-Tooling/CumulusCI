# Fix sketch - #3506: when clause support for flow steps which call other flows

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `cli`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3506>

## Bug

-   `cumulusci/core/flowrunner.py:660-672` - when the step has a `task:` key, the StepSpec is built with `when=step_config.get("when")`. - `cumulusci/core/flowrunner.py:674-697` - the `flow:` branch recurses via `_visit_step(...)` passing only `parent_options`, `parent_ui_options`, and `from_flow`; it never reads or propagates `step_config.get("when")`. Any `when:` clause attached to a flow-call...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` - confirmed silent-failure foot-gun the user reported.

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

`cumulusci/tests/triage/test_issue_3506.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3506:`).
