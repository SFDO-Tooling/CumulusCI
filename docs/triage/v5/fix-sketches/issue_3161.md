# Fix sketch — #3161: Ability to Hide Option Values When Using Task Options

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3161>

## Bug

A masking infrastructure was added (task-option metadata can opt in via `sensitive: True`), but: 1. The Robot `vars` option is not marked sensitive (`cumulusci/tasks/robotframework/robotframework.py:54-56`). 2. There's no CLI/Robot-side flag for the user to mark an ad-hoc `-o` value as sensitive.

## Target

`cumulusci/core/flowrunner.py` lines 300-320

## Recommended approach (from triage narrative)

-   pass1: `closed:stale-24mo` — 4yr; partial fix in place.
-   pass2 labels: `enhancement,stale,partially-implemented`

---

<!-- subagent 5 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3161.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3161:`).
