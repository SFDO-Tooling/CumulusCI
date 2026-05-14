# Fix sketch — #3602: Need Chrome/Firefox options(browser options/capabilities) in 'Open Test Browser' Keyword

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `robotframework`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3602>

## Bug

-   `cumulusci/robotframework/SalesforcePlaywright.py:60-62` — `def open_test_browser(self, size=None, useralias=None, wait=True, record_video=None):` has no `browser_options`/`extra_options`/`**kwargs` hook. - `cumulusci/robotframework/Salesforce.robot:103` — Selenium keyword signature `[Arguments]  ${size}=...  ${alias}=${NONE}  ${wait}=True  ${useralias}=${NONE}` — same gap. - `cumulusci/ro...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   Approach (Playwright): add a `browser_options: dict | None = None` kwarg; pass through to `new_browser` (browser-launch options) and a separate `context_options` dict merged into the `new_context` call.
-   Approach (Selenium): expose a `${EXTRA_CHROME_OPTIONS}` variable / list argument honoured by `Get Chrome Options`; alternatively add an `extra_options` argument to `Open Test Browser` and pipe through to `Create Webdriver With Retry`.
-   Target: `cumulusci/robotframework/SalesforcePlaywright.py:60-117`; `cumulusci/robotframework/Salesforce.robot:77-168`.
-   Size: medium (~30-60 lines across both implementations + tests + docs).
-   Risk: low — additive parameter with safe default.
-   API break: no (default `None` preserves current behaviour).

**Recommended action**:

-   pass1: `keep-open` — reasonable, scoped feature ask; age <36mo; no PR yet; tractable medium-sized contribution.
-   pass2 labels: `enhancement, robotframework, playwright, good-second-issue`
-   triage test: `cumulusci/tests/triage/test_issue_3602.py`

<!-- =============== R3 sub14 =============== -->

# Subagent 14 — scratch-org-config theme, Round 3

Working tree: `.worktrees/repro-scratch` on `worktree/repro/scratch` off `origin/dev` at `1925a3083`.

Triaged 3 issues (#3910, #3306, #710). All three remain actionable on dev: #3910 has an open fix PR; #3306 and #710 are never-implemented enhancements.

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3602.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3602:`).
