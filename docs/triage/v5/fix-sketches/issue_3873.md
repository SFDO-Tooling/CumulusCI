# Fix sketch — #3873: Standalone Robot Framework Library for Selenium-Based Salesforce Automation (Inspired by Copado QForce)

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `robotframework`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3873>

## Bug

-   `cumulusci/robotframework/base_library.py:1-39` — `BaseLibrary` lazily resolves `cumulusci.robotframework.CumulusCI`, `cumulusci.robotframework.Salesforce`, `cumulusci.robotframework.SalesforceAPI` libraries through Robot's `BuiltIn`, which require a CumulusCI project context. - `cumulusci/robotframework/Salesforce.py:20-28` — imports `cumulusci.robotframework.locator_manager`, `faker_mixin`...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   Approach: factor a UI-only subset out of `cumulusci.robotframework.*` into a sibling distribution (e.g. `salesforce-robot-library`) that depends only on Selenium/Playwright + the locator dictionaries; have CumulusCI's Robot task consume that subset.
-   Target: package layout change spanning `cumulusci/robotframework/` and `pyproject.toml`.
-   Size: large (>100 lines, design change + new distribution).
-   Risk: medium — must not break existing tasks/keywords.
-   API break: no (additive new distribution).

**Recommended action**:

-   pass1: `keep-open` — reasonable architectural request, age <24mo, no community PR yet; worth retaining as roadmap signal.
-   pass2 labels: `enhancement, robotframework, scope-large`
-   triage test: n/a — no concrete API to xfail against.

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

_None yet — add a regression test as part of the fix-PR._.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3873:`).
