# Fix sketch - #3570: Feature Request: Flow "finally" or "error" path

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `cli`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3570>

## Bug

-   `cumulusci/core/flowrunner.py` - only `ignore_failure` (mapped to `StepSpec.allow_failure`, line 122/144) and the `finally:` Python clause inside `flow.run()` (line 500) handle failures. There is no flow-step type for `finally:` / `on_error:` / `cleanup:` / `always_run`. `rg "finally|on_error|on_failure|always_run"` confirms. - `_run_step` (line 503-536) re-raises on `result.exception` if no...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` - design-level feature, but problem is real (rollback, notify on partial failure).

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

`cumulusci/tests/triage/test_issue_3570.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3570:`).
