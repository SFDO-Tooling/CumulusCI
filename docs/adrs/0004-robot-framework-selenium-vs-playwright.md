---
date: 2026-04-27
status: Proposed
author: "<!--@jstvz-->"
---

# 4. Robot Framework: Selenium Locator Maintenance vs Playwright Migration

## Context and Problem Statement

CumulusCI's Robot Framework tests use Selenium 3 (pinned `selenium<4`) with versioned locator dictionaries (one Python file per Salesforce API version). Per-release locator maintenance stopped due to team capacity constraints — no new locator file has been added since API v56 (current Salesforce production is v66, ~10 versions stale).

Three developments change the calculus:

1. **Agent-era token budgets.** Automated agents can absorb mechanical maintenance (locator diffs, test updates). The question is no longer "do we have engineers for this," it is "what is the per-release cost in agent tokens, and which path has the lower trajectory."
2. **Shadow DOM migration.** Salesforce continues migrating components from Aura to LWC. LWC components render inside shadow DOM. Selenium 3 cannot pierce shadow DOM at all; Selenium 4 can, but only through verbose chained traversal. This creates a structural ceiling for the Selenium-based approach that grows with every Salesforce release.
3. **Playwright maturity.** `robotframework-browser` is stable, ships Playwright bindings for Robot Framework, and provides accessibility-tree-first selectors that auto-pierce shadow DOM at any depth.

We need to decide CumulusCI's Robot Framework path: continue Selenium with agent-driven maintenance, migrate to Playwright, or run both.

### Assumptions

-   Agent tokens are abundant for mechanical tasks.
-   Salesforce will continue Aura→LWC migration each release; shadow DOM surface area grows monotonically.
-   Downstream consumers (NPSP, EDA, OFM, V4S, etc.) currently depend on the `sf:` locator prefix and Salesforce.robot resource.
-   `robotframework-browser` is a viable production library (3.x current, actively maintained).

### Constraints

-   **Selenium 3 cannot pierce shadow DOM.** Verified empirically: 0 matches for `List View Controls` button in `forms.robot`.
-   **Selenium 4 can pierce shadow DOM** via `WebElement.shadow_root`, but only via explicit chained traversal through every boundary.
-   **Backward compatibility.** Downstream consumers use the `sf:` prefix today. Migration cost is real.
-   **`robotframework-browser` requires runtime install.** `cci robot install_playwright` adds Node.js + Playwright binaries to the dev environment. Already supported as an optional path.

## Evidence from PoC

PoC ran on `robot-poc` scratch org (API v66) over two sessions. Spec: [`docs/superpowers/specs/2026-04-27-robot-framework-comparison-poc-design.md`](../superpowers/specs/2026-04-27-robot-framework-comparison-poc-design.md). Plan: [`docs/superpowers/plans/2026-04-27-robot-framework-comparison-poc.md`](../superpowers/plans/2026-04-27-robot-framework-comparison-poc.md). Selenium 4 verification scripts and findings: [`docs/superpowers/evidence/2026-04-27-robot-poc/`](../superpowers/evidence/2026-04-27-robot-poc/).

### Track A — Selenium 3 locator refresh (v56 → v66)

| Metric                                               | Result                                                                                                                                                                                    |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Versioned locator overrides added (`locators_66.py`) | **4** (`actions`, `app_launcher.current_app`, `list_view_menu.button`, `record.related.count`)                                                                                            |
| Selenium test pass rate (11 suites)                  | **101 / 102**                                                                                                                                                                             |
| Unfixable failure                                    | **1** — `forms.robot::radiobutton` (List View Controls in shadow DOM)                                                                                                                     |
| Page object pass rate (4 suites)                     | **29 / 34**                                                                                                                                                                               |
| Page object failures                                 | **5** — inline locators in `ObjectManagerPageObject.py` (Save button changed `<input>`→`<button>`, sidebar link text changed). These are inline locators outside the versioning system.   |
| Locator durability audit                             | 14 / 41 (34%) reference Aura internals (`uiModal`, `oneActionsRibbon`, `forceFormPageError`, `force_relatedListContainer`); 14 / 41 (34%) use SLDS-stable references; 13 / 41 (32%) ARIA. |
| Surface area                                         | 41 versioned locators, ~37 keywords in `Salesforce.py`, page objects, form_handlers dispatch — full system to maintain.                                                                   |

### Track B — Playwright keyword port (10 keywords)

| Metric                                      | Result                                                                                                                                                                                                                                                                          |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Keywords added to `SalesforcePlaywright.py` | **10** (`open_app_launcher`, `select_app_launcher_app`, `select_app_launcher_tab`, `populate_field`, `populate_form`, `click_modal_button`, `wait_until_modal_is_open`, `wait_until_modal_is_closed`, `click_related_list_button`, `get_related_list_count`)                    |
| Version-specific locators required          | **0**                                                                                                                                                                                                                                                                           |
| Selectors used                              | CSS, `text=`, SLDS classes (`section.slds-modal`, `article.slds-card`, etc.) — public ARIA / SLDS contract                                                                                                                                                                      |
| `@selenium_retry` equivalent needed         | **No** — Playwright auto-wait built in                                                                                                                                                                                                                                          |
| End-to-end test execution                   | Blocked by **pre-existing bug** in `SalesforcePlaywright.wait_until_salesforce_is_ready` (URL regex never matches; same bug breaks the existing baseline `playwright.robot` suite — predates this PoC). Keywords are structurally correct, infrastructure needs a separate fix. |

### Selenium 4 shadow DOM verification (post-PoC, real org)

Tested empirically against the same scratch org with `selenium==4.43.0` and headless Chrome. Target: `button[title='List View Controls']` on `/lightning/o/Account/list` (the failing element from `forms.robot`).

| Measurement                                     | Value                                                                                                                                                                       |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shadow roots on a single Account list view page | **452**                                                                                                                                                                     |
| Selenium 3 XPath/CSS matches in light DOM       | **0**                                                                                                                                                                       |
| Shadow boundary depth to reach the button       | **6 hops**                                                                                                                                                                  |
| Host chain (button → outer)                     | `lightning-button-menu` → `lst-list-view-manager-settings-menu` → `lst-list-view-manager-header` → `lst-common-list-internal` → `lst-list-view-manager` → `lst-object-home` |
| Outermost host findable in light DOM            | Yes (1 match)                                                                                                                                                               |
| Selenium 4 traversal cost                       | **~14 lines** (7 `find_element` + 6 `shadow_root` accesses) per shadow-DOM-bound element                                                                                    |
| Playwright equivalent                           | `page.get_by_role("button", name="List View Controls").click()` — **1 line**, auto-pierces all 6 boundaries                                                                 |

The host chain contains internal LWC component names (`lst-*`) that are implementation details, not a public contract — comparable in brittleness to the Aura classes (`force_*`, `uiModal`) we already pay for. Each rename across releases = a broken locator chain.

### Effort comparison (this PoC, agent-time)

These are observed, not modeled. They are directionally correct, not precise.

| Phase                                      | Track A (Selenium)                                                                                                                                           | Track B (Playwright)                                                         |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Tool calls (this session)                  | ~50+ (test runs, log parsing, locator debugging, audit)                                                                                                      | ~6 (subagent run + viewport int fix)                                         |
| Iterations to working state                | Multiple — `record.related.count` named-vs-positional `.format()` bug, breadcrumb wrong-element-class assumption, page object inline locators (5 unresolved) | Single — keywords compiled correctly first try; one viewport `int()` bug fix |
| Wall-clock agent work (excl. test runtime) | ~45 min                                                                                                                                                      | ~5 min                                                                       |
| Lines of working code added                | 56 (4 locators + 3 test fixtures)                                                                                                                            | 125 (10 keywords)                                                            |
| Code-output efficiency                     | ~1.2 lines/min                                                                                                                                               | ~25 lines/min                                                                |
| Unresolved at end                          | 5 inline-locator failures in page objects + 1 unfixable shadow DOM                                                                                           | 1 pre-existing infrastructure bug                                            |

**Caveat (sample-size bias):** the 10 Playwright keywords ported are the easier surface (modal, app launcher, simple form fill). The harder surface — page object model, `form_handlers.py` dispatch table, label-locator strategy, related-list popups — was not ported. The "~25× efficiency" headline is real for the tested surface; the full-port number will likely be lower (probably 3–5×, not 25×).

### Per-release maintenance trajectory

What it actually costs to support a new Salesforce API version, per path:

| Path                      | Per-release cost                                                                                                                                                                                                                        | Trajectory                                                                                             |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Selenium 3 (current)      | 4 versioned overrides + ~5 inline page-object fixes + growing unfixable failures from new shadow-DOM-bound elements                                                                                                                     | **Worsening** — shadow DOM is monotonically increasing                                                 |
| Selenium 4 (hypothetical) | 4 versioned overrides + N rewrites of existing locators using 14-line chained shadow_root traversal + brittleness from `lst-*` internal names + significant one-time upgrade cost (selenium 3→4, seleniumlibrary 5→6 with API breakage) | **Better than Selenium 3 but still version-tied**; still pays the locator-architecture maintenance tax |
| Playwright                | Near-zero. ARIA/SLDS public contract is stable; auto-wait removes flakiness; no version-keyed files                                                                                                                                     | **Effectively flat**                                                                                   |

## Decision

### Considered Options

**Option 1 — Selenium 3, agent-maintained**

-   Good: zero migration cost; downstream consumers unaffected
-   Good: 4 overrides for 10 versions is mechanically tractable
-   Bad: shadow DOM ceiling permanent (verified: 1 of 102 tests already unfixable; trajectory is worsening every release)
-   Bad: 34% of locators reference Aura internals scheduled for removal
-   Bad: inline locators in page objects (`ObjectManagerPageObject.py`) bypass versioning entirely — 5 PoC failures

**Option 2 — Playwright migration, deprecation period for Selenium**

-   Good: zero version-specific locators (verified)
-   Good: shadow DOM auto-pierce (1 line vs Selenium 4's 14 lines per element)
-   Good: accessibility-first selectors map to a stable public contract (ARIA/SLDS) rather than internal class names
-   Good: auto-wait eliminates `@selenium_retry`, reducing flakiness
-   Bad: requires porting ~37 keywords (10 done, 27 to go); harder surfaces (page object model, form_handlers, label strategy) untested in PoC
-   Bad: breaking change for downstream `sf:` prefix consumers — requires coordinated migration
-   Bad: adds Node.js + Playwright binary install footprint
-   Bad: pre-existing `wait_until_salesforce_is_ready` bug must be fixed first

**Option 3 — Dual-track (open-ended), maintain both**

-   Good: preserves backward compatibility indefinitely
-   Bad: pays both maintenance costs forever — Selenium's growing shadow DOM ceiling AND Playwright's keyword port
-   Bad: contributors must learn both libraries
-   Bad: defers the inevitable; two surfaces to test, document, and support
-   Bad: weak on its own merits — chosen mainly to avoid making a decision

**Option 4 — Selenium 4 upgrade, keep architecture**

-   Good: nominally addresses shadow DOM ceiling
-   Good: smaller migration surface than Playwright (no keyword rewrites)
-   Bad: **verified** that traversal requires 14 lines per shadow-DOM element through internal LWC names (`lst-*`); brittleness equivalent to current Aura-class approach
-   Bad: significant upgrade cost (selenium 3→4 API changes, seleniumlibrary 5→6 breaking changes)
-   Bad: still pays the per-release locator architecture tax (versioned files, locator_manager indirection, inline locator drift)
-   Bad: the 14-line traversal pattern accumulates fast — at 452 shadow roots per page, anything depth-bound is verbose

### Decision Outcome

**Recommended: Option 2 — Playwright migration with a time-bounded Selenium deprecation period.**

Evidence summary supporting Option 2:

1. **Maintenance cost trajectory is the dominant factor.** Selenium 3 worsens monotonically (shadow DOM ceiling grows). Selenium 4 is better but still version-tied with brittle internal names. Playwright is effectively flat. Over any reasonable horizon, Playwright wins.
2. **Selenium 4 does not actually solve the shadow DOM problem at scale.** Verified empirically: 14 lines of chained traversal per element through internal LWC component names. The Aura-brittleness pattern just shifts to LWC-brittleness.
3. **Playwright keyword development is meaningfully cheaper for agents.** The PoC observed ~25× per-line efficiency on the easy surface. Even discounted to 3–5× on harder surfaces, it dominates the ongoing locator-refresh cost.
4. **The 10-keyword PoC validates feasibility.** Keywords compile correctly using public ARIA/SLDS selectors; no version-keyed files; auto-wait eliminates the retry decorator entirely.

Sub-decisions:

-   **Selenium 4 upgrade is no longer required.** The roadmap's `dep-modernization` todo can drop the `selenium<4` upgrade unless a Plan-B fallback is needed during the deprecation period.
-   **`SalesforcePlaywright.wait_until_salesforce_is_ready` bug must be fixed** as a first step (pre-existing; blocks all Playwright E2E execution including the existing baseline `playwright.robot` suite).
-   **Inline locators in page objects must be migrated** as part of the Playwright port (currently bypass the versioning system, contribute 5 of 5 page object failures in the PoC).

### Migration Path

Phased plan:

**Phase M1 — Unblock Playwright (1 PR)**

-   Fix `SalesforcePlaywright.wait_until_salesforce_is_ready` URL regex bug
-   Verify existing `playwright.robot` baseline suite passes
-   Verify the new `e2e_comparison.robot` test passes

**Phase M2 — Port remaining keywords (~3–5 PRs)**

-   Port the remaining ~27 keywords from `Salesforce.py` (the harder surface: page object model, `form_handlers` dispatch, label strategy, related-list popups, performance keywords)
-   Each PR ports a coherent group, includes a Playwright-side test, and is reviewed independently
-   Track per-keyword effort and update this ADR with the realized full-port cost (sample-size caveat addresses this)

**Phase M3 — Compatibility surface for downstream**

-   Provide `SalesforceCompat.robot` resource that re-exports Playwright keywords under the existing Selenium-compatible names (`Open Test Browser`, `Populate Form`, `Click Modal Button`, etc.)
-   For the `sf:` locator prefix: provide either a deprecation path with per-locator migration tooling, or a runtime translator that maps the most-used `sf:` paths to Playwright selectors during the deprecation window
-   Decide based on downstream usage survey (see Phase M4)

**Phase M4 — Downstream migration**

-   Survey `sf:` prefix usage across NPSP, EDA, OFM, V4S, and any other public consumers
-   Open coordinated PRs against each consumer:
    -   Replace `Resource cumulusci/robotframework/Salesforce.robot` with the Playwright equivalent (or `SalesforceCompat.robot` during the deprecation window)
    -   Mechanical replacement of `sf:` locator references where automatable
    -   Coordinate release/branch strategy with downstream maintainers
-   Provide a migration guide in `docs/robot-playwright-migration.md`
-   Provide a `cci robot migrate-to-playwright` task that does mechanical rewrites where possible

**Phase M5 — Deprecation and removal**

-   Mark `Salesforce.robot` (Selenium path) as deprecated on import (Robot Framework warning)
-   Set an end-of-life version (e.g. CCI 6.0 or two major versions out)
-   Remove Selenium path and `selenium`/`robotframework-seleniumlibrary` dependencies in the EOL release

**During Phases M1–M4**, the Selenium path remains available unchanged. Downstream consumers can migrate on their own schedule within the deprecation window. This is **time-bounded dual-track**, not the open-ended dual-track of Option 3.

## Consequences

-   **Positive:** Reduces ongoing Robot Framework maintenance to near-zero per Salesforce release. Eliminates the shadow DOM ceiling. Agent-driven keyword development becomes cheap.
-   **Positive:** Playwright's accessibility-first selectors are stable across releases, reducing test flakiness independent of agent maintenance.
-   **Positive:** Removes the `selenium<4` upgrade from the dependency-modernization queue.
-   **Negative:** Significant one-time migration cost — ~27 remaining keywords, downstream coordination, compatibility shim or migration tooling.
-   **Negative:** Breaking change for downstream consumers, even with a deprecation window. Coordination effort with NPSP, EDA, OFM, V4S maintainers.
-   **Negative:** Adds Node.js + Playwright binary dependency for users who run browser tests.
-   **Risk:** Sample-size bias — the 10-keyword PoC tested the easy surface. The harder keywords (page object model, form_handlers) may surface unforeseen complexity. Mitigation: Phase M2 is structured as ~5 independent PRs, each with its own validation, so the cost gets revealed incrementally rather than as a big-bang surprise.
-   **Risk:** Downstream maintainers may not have capacity to migrate. Mitigation: long deprecation window (≥1 major version), `SalesforceCompat.robot` shim, automated migration tooling.

## References

-   PoC spec: [`docs/superpowers/specs/2026-04-27-robot-framework-comparison-poc-design.md`](../superpowers/specs/2026-04-27-robot-framework-comparison-poc-design.md)
-   PoC implementation plan: [`docs/superpowers/plans/2026-04-27-robot-framework-comparison-poc.md`](../superpowers/plans/2026-04-27-robot-framework-comparison-poc.md)
-   Selenium 4 verification scripts and findings: [`docs/superpowers/evidence/2026-04-27-robot-poc/`](../superpowers/evidence/2026-04-27-robot-poc/)
-   [`robotframework-browser` (Playwright)](https://robotframework-browser.org/)
-   [Robot Framework SeleniumLibrary](https://robotframework.org/SeleniumLibrary/)
-   [Selenium 4 shadow DOM API](https://www.selenium.dev/documentation/webdriver/elements/finders/#shadow-dom)
-   [Salesforce Lightning Web Components (LWC)](https://developer.salesforce.com/docs/component-library/documentation/en/lwc)
