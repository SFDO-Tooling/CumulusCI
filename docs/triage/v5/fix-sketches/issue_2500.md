# Fix sketch — #2500: `ignore_failure` is not documented

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `docs`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/2500>

## Bug

`ignore_failure` is not documented

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

Add `### Ignore a Failed Step` (or `### Continue After a Failed Step`)
to `docs/config.md` immediately after the existing `### Skip a Flow Step`
section. Body should cover:

-   What it does: when `ignore_failure: True` is set on a step, an
    exception raised by that step does not abort the flow; subsequent
    steps still run.
-   A minimal YAML example (the existing `release_unlocked_production`
    snippet around line 783 already demonstrates it — link to it instead
    of duplicating).
-   Interaction with `^^step.return_value` references: downstream steps
    that reference a failed step's return values must defend against
    missing keys.
-   When NOT to use it: in CI, silently ignoring a failure hides
    regressions; prefer a `when:` clause for intentional conditional
    branching.
-   One sentence on the difference between `ignore_failure` (post hoc:
    swallow the exception) and `when:` (a priori: skip the step entirely).

This is a tiny, high-leverage docs PR — a strong candidate for a
`good-first-issue` label.

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_2500.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #2500:`).
