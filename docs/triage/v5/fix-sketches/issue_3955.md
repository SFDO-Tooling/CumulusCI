# Fix sketch — #3955: Open Test Browser - SalesforcePlaywright.robot

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `robotframework`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3955>

## Bug

-   `cumulusci/robotframework/SalesforcePlaywright.py:106` — `width, height = size.split("x", 1)` returns two `str` values. - `cumulusci/robotframework/SalesforcePlaywright.py:109-111` — the strings are forwarded directly: - Playwright contract requires `viewport.width` / `viewport.height` to be `int`, hence the runtime error `viewport.width: expected integer, got string` reported by the user ...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   Approach: cast both fragments to `int` immediately after splitting.
-   Target: `cumulusci/robotframework/SalesforcePlaywright.py:106`
-   Size: small (~1 line) — e.g. `width, height = (int(v) for v in size.split("x", 1))`
-   Risk: low — preserves all existing call sites; users were already passing the documented `WxH` string format.
-   API break: no.

**Recommended action**:

-   pass1: `keep-open` — clear, low-risk, single-line bug fix; great good-first-issue candidate.
-   pass2 labels: `bug, robotframework, playwright, good-first-issue`
-   triage test: `cumulusci/tests/triage/test_issue_3955.py`

---

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3955.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3955:`).
