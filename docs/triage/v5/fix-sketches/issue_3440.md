# Fix sketch — #3440: Enhance `default_package_path` to serve multi-package projects better

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `packaging`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3440>

## Bug

-   `cumulusci/core/config/project_config.py:517-525` — implementation is the simple "first packageDirectory with `default: true`" pattern; falls back to `force-app`, then `src`. No name-based lookup, no multi-package warning, no hard fail when both are missing.

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` — same multi-package umbrella as #2979 / #3429; would best be solved together.
-   pass2 labels: `severity:low,area:packaging,area:sfdx,area:multi-package`

---

<!-- subagent 1 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3440.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3440:`).
