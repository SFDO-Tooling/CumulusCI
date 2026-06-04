# Fix sketch - #675: Show full traceback for Python exceptions in robot keywords

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `robotframework`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/675>

## Bug

-   `cumulusci/tasks/robotframework/robotframework.py` configures listeners (`KeywordLogger`, `DebugListener`) but never sets `loglevel`/`logtitle`/`pythonpath` to surface Python tracebacks. `rg 'traceback|format_exc|format_tb' cumulusci/robotframework/` returns 0 matches; same for `cumulusci/tasks/robotframework/`. - Robot Framework's default behaviour: when a Python keyword raises, only `str(e...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   Approach: in `Robot.\_init_options`, default `options.loglevel`to include`TRACE`, OR install a small listener that captures `sys.exc_info()`in keyword-end events and emits a formatted traceback through`robot.api.logger.error`.

-   Target: `cumulusci/tasks/robotframework/robotframework.py:104` (`_init_options`).
-   Size: small (~10 lines).
-   Risk: low - additive listener; opt-out via options if needed.
-   API break: no.

**Recommended action**:

-   pass1: `closed:stale-24mo` - issue opened 2018-07, last activity 2018-09, ~8 years inactivity. Two simple workarounds exist (`-o loglevel:TRACE`, `traceback.format_exc()` in keywords). Surface as a tip in docs rather than keep the bug open.
-   pass2 labels: `cli-usability, robotframework, stale`
-   triage test: n/a - observable only in a robot run.

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

_None yet - add a regression test as part of the fix-PR._.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #675:`).
