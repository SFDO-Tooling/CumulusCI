---
date: 2026-04-27
status: Proposed
author: "@jstvz"
---

# 4. Robot Framework: Selenium Locator Maintenance vs Playwright Migration

## TL;DR

Migrate CumulusCI's Robot Framework browser-test infrastructure from Selenium 3 to `robotframework-browser` (Playwright) over a time-bounded deprecation period (Phases M1–M5, expected 6–12 months for the downstream-coordination tail). Selenium 4 is no longer required. The `sf:` locator prefix and `Salesforce.robot` resource remain available during deprecation; downstream consumers (NPSP, EDA, OFM, V4S) migrate on their own schedule with tooling support. Selenium per-release maintenance is tractable today (4 locator overrides bridged 10 API versions) but its shadow-DOM trajectory is structurally bad and Selenium 4 only shifts the brittleness from Aura to LWC at ~14× the verbosity (per single-element measurement; see body).

## Context and Problem Statement

CumulusCI's Robot Framework tests use Selenium 3 (pinned at [`pyproject.toml:54`](../../pyproject.toml) via `selenium<4` and [`pyproject.toml:50`](../../pyproject.toml) via `robotframework-seleniumlibrary<6`) with versioned locator dictionaries (one Python file per Salesforce API version). Per-release locator maintenance stopped due to team capacity constraints — no new locator file has been added since API v56 ([`locators_57.py`](../../cumulusci/robotframework/locators_57.py) is an identity copy of [`locators_56.py`](../../cumulusci/robotframework/locators_56.py); current Salesforce production is v66, ~10 versions stale).

Three developments change the calculus:

1. **Agent-era token budgets.** Automated agents can absorb mechanical maintenance (locator diffs, test updates). The question is no longer "do we have engineers for this," it is "what is the per-release cost in agent tokens, and which path has the lower trajectory."
2. **Shadow DOM migration.** Salesforce continues migrating components from Aura to LWC. LWC components render inside shadow DOM. Selenium 3 cannot pierce shadow DOM at all; Selenium 4 can, but only through verbose chained traversal. This creates a structural ceiling for the Selenium-based approach that grows with every Salesforce release.
3. **Playwright maturity.** `robotframework-browser` is stable, ships Playwright bindings for Robot Framework, and provides accessibility-tree-first selectors that auto-pierce shadow DOM at any depth.

We need to decide CumulusCI's Robot Framework path: continue Selenium with agent-driven maintenance, migrate to Playwright, or run both.

### Assumptions

-   Agent tokens are abundant for mechanical tasks.
-   Salesforce will continue Aura→LWC migration each release; shadow DOM surface area grows monotonically.
-   Downstream consumers (NPSP, EDA, OFM, V4S, etc.) currently depend on the `sf:` locator prefix and `Salesforce.robot` resource.
-   `robotframework-browser` is a viable production library (3.x current, actively maintained).

### Constraints

-   **Selenium 3 cannot pierce shadow DOM.** Verified empirically: 0 matches in light DOM for `List View Controls` button targeted by `forms.robot`.
-   **Selenium 4 can pierce shadow DOM** via `WebElement.shadow_root`, but only via explicit chained traversal through every boundary.
-   **Backward compatibility.** Downstream consumers use the `sf:` prefix today. Migration cost is real.
-   **`robotframework-browser` requires runtime install.** `cci robot install_playwright` adds Node.js + Playwright binaries to the dev environment. Already supported as an optional path.

## Evidence from PoC

> **Important caveat:** No Playwright end-to-end test passed during the PoC. The 10 Track B keywords were validated by static review and selector-strategy analysis, not by runtime execution. A pre-existing regex bug in [`SalesforcePlaywright.wait_until_salesforce_is_ready`](../../cumulusci/robotframework/SalesforcePlaywright.py) (line 165) blocks all Playwright E2E execution, including the existing baseline `playwright.robot` suite that predates this PoC. **Phase M1 fixes this as the first migration step.** The Playwright argument here rests on selector-strategy and shadow-DOM-piercing evidence, not on runtime test counts.

**Methodology in one paragraph.** Track A (Selenium 3) updated [`locators_66.py`](../../cumulusci/robotframework/locators_66.py) with 4 overrides and ran the 11-suite Selenium battery plus 4 page-object suites against a `robot-poc` scratch org (API v66). Track B (Playwright) added 10 keywords to [`SalesforcePlaywright.py`](../../cumulusci/robotframework/SalesforcePlaywright.py) using accessibility-first selectors. After the main PoC, Selenium 4.43.0 was installed in an isolated venv and tested against the same scratch org with two scripts ([`measure_nesting.py`](0004-evidence/measure_nesting.py), [`verify_shadow_dom.py`](0004-evidence/verify_shadow_dom.py)) to measure shadow-DOM traversal cost. All scripts and findings live under [`docs/adrs/0004-evidence/`](0004-evidence/) for reproduction.

### Track A — Selenium 3 locator refresh (v56 → v66)

| Metric                                                                                                | Result                                                                                                                                                                                                                                                           |
| ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Versioned locator overrides added ([`locators_66.py`](../../cumulusci/robotframework/locators_66.py)) | **4** (`actions`, `app_launcher.current_app`, `list_view_menu.button`, `record.related.count`)                                                                                                                                                                   |
| Selenium test pass rate (11 suites)                                                                   | **101 / 102**                                                                                                                                                                                                                                                    |
| Unfixable failure                                                                                     | **1** — `forms.robot::radiobutton` (List View Controls in shadow DOM)                                                                                                                                                                                            |
| Page object pass rate                                                                                 | **29 / 34** (34 cases across 4 page-object suites)                                                                                                                                                                                                               |
| Page object failures                                                                                  | **5** — inline locators in [`ObjectManagerPageObject.py`](../../cumulusci/robotframework/pageobjects/ObjectManagerPageObject.py) (Save button changed `<input>`→`<button>`, sidebar link text changed). These are inline locators outside the versioning system. |
| Locator durability audit                                                                              | 14 / 41 (34%) reference Aura internals (`uiModal`, `oneActionsRibbon`, `forceFormPageError`, `force_relatedListContainer`); 14 / 41 (34%) use SLDS-stable references; 13 / 41 (32%) ARIA.                                                                        |
| Surface area                                                                                          | 41 versioned locators, ~37 keywords in `Salesforce.py`, page objects, form_handlers dispatch — full system to maintain.                                                                                                                                          |

### Track B — Playwright keyword port (10 keywords)

| Metric                                                                                               | Result                                                                                                                                                                                                                                                       |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Keywords added ([`SalesforcePlaywright.py`](../../cumulusci/robotframework/SalesforcePlaywright.py)) | **10** (`open_app_launcher`, `select_app_launcher_app`, `select_app_launcher_tab`, `populate_field`, `populate_form`, `click_modal_button`, `wait_until_modal_is_open`, `wait_until_modal_is_closed`, `click_related_list_button`, `get_related_list_count`) |
| Version-specific locators required                                                                   | **0**                                                                                                                                                                                                                                                        |
| Selectors used                                                                                       | CSS, `text=`, SLDS classes (`section.slds-modal`, `article.slds-card`, etc.) — public ARIA / SLDS contract                                                                                                                                                   |
| `@selenium_retry` equivalent needed                                                                  | **No** — Playwright auto-wait built in                                                                                                                                                                                                                       |
| End-to-end test execution                                                                            | **Did not pass during PoC.** Pre-existing `wait_until_salesforce_is_ready` regex bug (see Important caveat above). Keywords compile and the selector strategy is sound; runtime validation is Phase M1.                                                      |

### Selenium 4 shadow DOM verification (post-PoC, real org)

Tested empirically against the same scratch org with `selenium==4.43.0` and headless Chrome. Target: `button[title='List View Controls']` on `/lightning/o/Account/list` (the failing element from `forms.robot`). Scripts and raw findings: [`docs/adrs/0004-evidence/`](0004-evidence/).

| Measurement                                                                                                                | Value                                                                                                                                                                       |
| -------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shadow hosts on a single Account list view page (count of elements with `shadowRoot`, NOT a count of unreachable elements) | **452**                                                                                                                                                                     |
| Selenium 3 XPath/CSS matches in light DOM                                                                                  | **0**                                                                                                                                                                       |
| Shadow boundary depth to reach the button                                                                                  | **6 hops**                                                                                                                                                                  |
| Host chain (button → outer)                                                                                                | `lightning-button-menu` → `lst-list-view-manager-settings-menu` → `lst-list-view-manager-header` → `lst-common-list-internal` → `lst-list-view-manager` → `lst-object-home` |
| Outermost host findable in light DOM                                                                                       | Yes (1 match)                                                                                                                                                               |
| Selenium 4 traversal cost                                                                                                  | **~14 statements** per element: 1 `find_element` for the outermost host + 6 × (`shadow_root` access + `find_element` into next layer) + 1 final action = 14 statements.     |
| Playwright equivalent                                                                                                      | `page.get_by_role("button", name="List View Controls").click()` — **1 line**, auto-pierces all 6 boundaries                                                                 |

**Single-sample caveat for Selenium 4.** This is one element on one page. Other shadow-DOM-bound elements in the test suite may be 1–2 hops shallow or 6+ hops deep — we did not measure the distribution. The 452 shadow-host count says "Lightning is heavily LWC-componentized," not "452 elements are unreachable." What generalizes from this measurement is the _architectural concern_: the host-chain names (`lst-list-view-manager`, `lst-list-view-manager-settings-menu`, etc.) are LWC-internal implementation details, comparable in stability to Aura classes (`force_*`, `uiModal`) we already pay for today. The specific 14-statement cost is a single data point; the qualitative claim — "Selenium 4 shifts brittleness from Aura to LWC, it does not eliminate it" — is the durable conclusion.

### Effort comparison (this PoC, agent-time)

All numbers below are from direct observation; they give an accurate sense of scale but aren't statistically precise.

| Phase                                      | Track A (Selenium)                                                                                                                                           | Track B (Playwright)                                                         |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Tool calls (this session)                  | ~50+ (test runs, log parsing, locator debugging, audit)                                                                                                      | ~6 (subagent run + viewport int fix)                                         |
| Iterations to working state                | Multiple — `record.related.count` named-vs-positional `.format()` bug, breadcrumb wrong-element-class assumption, page object inline locators (5 unresolved) | Single — keywords compiled correctly first try; one viewport `int()` bug fix |
| Wall-clock agent work (excl. test runtime) | ~45 min                                                                                                                                                      | ~5 min                                                                       |
| Lines of working code added                | 56 (4 locators + 3 test fixtures)                                                                                                                            | 125 (10 keywords)                                                            |
| Code-output rate                           | ~1.2 lines/min                                                                                                                                               | ~25 lines/min                                                                |
| Unresolved at end                          | 5 inline-locator failures in page objects + 1 unfixable shadow DOM                                                                                           | 1 pre-existing infrastructure bug                                            |

**On the rate ratio.** Track B's ~25 lines/min is a rate, not a ratio. Track A's debug-heavy work produced ~1.2 lines/min, which gives a ratio of roughly **~20× on the surface tested**. Two reasons not to take this number as the full-port headline:

1. **The two rates are not directly comparable.** Track A's lines are mostly XPath fragments and test fixtures debugged against a live org. Track B's lines are mostly keyword bodies and docstrings written from scratch. Lines-per-minute is a rough engineering proxy, not a precise metric.
2. **Sample-size bias.** The 10 ported keywords are the easier surface (modals, app launcher, simple form fill). The harder surface — page object model, [`form_handlers.py`](../../cumulusci/robotframework/form_handlers.py) dispatch table, label-locator strategy, related-list popups — was not ported. Those keywords contain non-trivial Python logic that doesn't get cheaper just because the underlying browser library changed.

A defensible engineering estimate for the **full port** is **3–5× faster than equivalent Selenium maintenance**, not 20×. This is not a measured number; it is a calibrated estimate based on the complexity of the unported surface. The lower bound (3×) assumes the harder keywords are dominated by Python control flow (page object model, `form_handlers` dispatch, label strategy) that costs roughly the same in either library; the upper bound (5×) assumes Playwright still wins on selector strategy and auto-wait even where the Python logic is comparable. Phase M2 will produce real per-keyword data that should refine this estimate (and we will publish a follow-up ADR with realized numbers — see Consequences).

### Per-release maintenance trajectory

What it actually costs to support a new Salesforce API version, per path:

| Path                      | Per-release cost                                                                                                                                                                                                                                | Trajectory                                                                                             |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Selenium 3 (current)      | 4 versioned overrides + ~5 inline page-object fixes + growing unfixable failures from new shadow-DOM-bound elements                                                                                                                             | **Worsening** — shadow DOM is monotonically increasing                                                 |
| Selenium 4 (hypothetical) | 4 versioned overrides + N rewrites of existing locators using ~14-statement chained `shadow_root` traversal + brittleness from `lst-*` internal names + significant one-time upgrade cost (selenium 3→4, seleniumlibrary 5→6 with API breakage) | **Better than Selenium 3 but still version-tied**; still pays the locator-architecture maintenance tax |
| Playwright                | Near-zero. ARIA/SLDS public contract is stable; auto-wait removes flakiness; no version-keyed files                                                                                                                                             | **Effectively flat**                                                                                   |

## Decision

### Considered Options

**Option 1 — Selenium 3, agent-maintained**

-   Good: zero migration cost; downstream consumers unaffected
-   Good: 4 overrides for 10 versions is mechanically tractable
-   Bad: shadow DOM ceiling permanent (verified: 1 of 102 tests already unfixable; trajectory is worsening every release)
-   Bad: 34% of locators reference Aura internals scheduled for removal
-   Bad: inline locators in page objects ([`ObjectManagerPageObject.py`](../../cumulusci/robotframework/pageobjects/ObjectManagerPageObject.py)) bypass versioning entirely — 5 PoC failures

**Option 2 — Playwright migration, deprecation period for Selenium**

-   Good: zero version-specific locators (verified)
-   Good: shadow DOM auto-pierce (1 line vs Selenium 4's ~14 statements per element)
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
-   Bad: **verified** that traversal requires ~14 statements per shadow-DOM element through internal LWC names (`lst-*`); brittleness equivalent to current Aura-class approach (single-sample caveat acknowledged — see Selenium 4 section)
-   Bad: significant upgrade cost (selenium 3→4 API changes, seleniumlibrary 5→6 breaking changes)
-   Bad: still pays the per-release locator architecture tax (versioned files, locator_manager indirection, inline locator drift)

**Option 5 — Reduce Robot Framework surface**

-   Good: minimal cost — drop low-value tests, keep only critical-path coverage
-   Good: this is implicitly already the strategy (locator maintenance has been stopped since v56)
-   Bad: ducks the architectural question — the remaining tests still hit the same shadow DOM ceiling and the same versioned-locator maintenance tax
-   Bad: erodes test coverage over time without a deliberate plan for what replaces it
-   Bad: leaves downstream consumers in the lurch — they cannot reduce surface as easily as we can
-   Verdict: **dismissed.** Reasonable as a coping strategy but not an architectural answer; can be combined with any of the other options as a separate decision.

**Option 6 — Hybrid: new tests in Playwright, freeze existing Selenium tests**

-   Good: avoids the upfront keyword-port cost; new investment goes to Playwright
-   Good: existing tests keep working until they don't; no big-bang migration moment
-   Bad: Selenium tests rot quietly — when one breaks, no one is on the hook to fix it
-   Bad: contributors still face the two-library cognitive load (read Selenium tests, write Playwright tests)
-   Bad: indefinite half-life; the Selenium tail can persist for years and silently degrade coverage
-   Bad: no migration path for downstream consumers — they remain stuck on Selenium with no support story
-   Verdict: **dismissed.** A softer Option 3; same fundamental problem (no decision) without even Option 3's "we maintain both" commitment. The structured deprecation in Option 2's Phase M5 is materially better than passive rot.

### Decision Outcome

**Decision: Adopt Option 2 — Playwright migration with a time-bounded Selenium deprecation period.**

Evidence summary supporting Option 2:

1. **Maintenance cost trajectory is the dominant factor.** Selenium 3 worsens monotonically (shadow DOM ceiling grows). Selenium 4 is better but still version-tied with brittle internal names. Playwright is effectively flat. Over any reasonable horizon, Playwright wins.
2. **Selenium 4 does not actually solve the shadow DOM problem at scale.** Verified empirically: ~14 statements of chained traversal per element through internal LWC component names (single-sample caveat acknowledged). The Aura-brittleness pattern just shifts to LWC-brittleness.
3. **Playwright keyword development is meaningfully cheaper for agents.** The PoC observed ~20× per-line ratio on the easy surface; calibrated full-port estimate is **3–5×**. Either dominates the ongoing locator-refresh cost.
4. **The 10-keyword PoC validates feasibility at the structural level.** Keywords compile correctly using public ARIA/SLDS selectors; no version-keyed files; auto-wait eliminates the retry decorator entirely. **Runtime validation is Phase M1.**

Sub-decisions:

-   **Selenium 4 upgrade is no longer required.** The roadmap's `dep-modernization` todo can drop the `selenium<4` upgrade unless a Plan-B fallback is needed during the deprecation period.
-   **`SalesforcePlaywright.wait_until_salesforce_is_ready` bug must be fixed** as a first step (pre-existing; blocks all Playwright E2E execution including the existing baseline `playwright.robot` suite).
-   **Inline locators in page objects must be migrated** as part of the Playwright port (currently bypass the versioning system, contribute 5 of 5 page object failures in the PoC).

### Migration Path

Phased plan with realistic durations.

**Phase M1 — Unblock Playwright (1 PR, ~1 week)**

-   Fix [`SalesforcePlaywright.wait_until_salesforce_is_ready`](../../cumulusci/robotframework/SalesforcePlaywright.py) URL regex bug
-   Verify existing `playwright.robot` baseline suite passes
-   Verify the new `e2e_comparison.robot` test passes

**Phase M2 — Port remaining keywords (~3–5 PRs, ~1–2 months)**

-   Port the remaining ~27 keywords from `Salesforce.py` (the harder surface: page object model, `form_handlers` dispatch, label strategy, related-list popups, performance keywords)
-   Each PR ports a coherent group, includes a Playwright-side test, and is reviewed independently
-   Track per-keyword effort to refine the 3–5× estimate
-   Outcomes (realized full-port cost, any unforeseen complexity) will be published as a follow-up ADR rather than amending this one — ADRs are durable records by design

**Phase M3 — Compatibility surface for downstream (~2–4 weeks for shim; runtime translator deferred unless data warrants)**

-   Provide `SalesforceCompat.robot` resource that re-exports Playwright keywords under the existing Selenium-compatible names (`Open Test Browser`, `Populate Form`, `Click Modal Button`, etc.). **This is straightforward — days to a couple of weeks of engineering.**
-   For the `sf:` locator prefix: choose between (a) per-locator migration tooling that rewrites consumers' test files mechanically, or (b) a runtime translator that maps `sf:` paths to Playwright selectors at locator-resolution time. **The shim is cheap; a runtime translator is substantial — weeks of engineering with non-trivial parsing of parameterized format strings and risk of subtle correctness bugs. We will only build the runtime translator if the downstream usage survey (Phase M4) shows it is justified.**
-   Decide based on downstream usage survey (see Phase M4)

**Phase M4 — Downstream migration (~6–12 months across all consumers)**

-   Survey `sf:` prefix usage across NPSP, EDA, OFM, V4S, and any other public consumers
-   Open coordinated PRs against each consumer:
    -   Replace `Resource cumulusci/robotframework/Salesforce.robot` with the Playwright equivalent (or `SalesforceCompat.robot` during the deprecation window)
    -   Mechanical replacement of `sf:` locator references where automatable
    -   Coordinate release/branch strategy with downstream maintainers
-   Provide a migration guide in `docs/robot-playwright-migration.md`
-   Provide a `cci robot migrate-to-playwright` task that does mechanical rewrites where possible

**Realistic expectations for Phase M4.** Each downstream PR is a multi-week coordination effort with that project's review, CI, and release cycle. NPSP in particular has substantial Robot Framework coverage and a slower release cadence. The deprecation window must accommodate these cycles; we expect the migration tail to span **6–12 months across all four consumers**, not weeks. Capacity at the downstream maintainer side is the binding constraint, not CCI engineering effort.

**Phase M5 — Deprecation and removal (after Phase M4 completes; soft-deprecation can begin earlier)**

-   Mark `Salesforce.robot` (Selenium path) as deprecated on import (Robot Framework warning)
-   Set an end-of-life version (e.g. CCI 6.0 or two major versions out)
-   Remove Selenium path and `selenium`/`robotframework-seleniumlibrary` dependencies in the EOL release

**During Phases M1–M4**, the Selenium path remains available unchanged. Downstream consumers can migrate on their own schedule within the deprecation window. This is **time-bounded dual-track**, not the open-ended dual-track of Option 3.

## Consequences

-   **Positive:** Reduces ongoing Robot Framework maintenance to near-zero per Salesforce release. Eliminates the shadow DOM ceiling. Agent-driven keyword development becomes cheap.
-   **Positive:** Playwright's accessibility-first selectors are stable across releases, reducing test flakiness independent of agent maintenance.
-   **Positive:** Removes the `selenium<4` upgrade from the dependency-modernization queue.
-   **Negative:** Significant one-time migration cost — ~27 remaining keywords, downstream coordination, compatibility shim or migration tooling.
-   **Negative:** Breaking change for downstream consumers, even with a deprecation window. Coordination effort with NPSP, EDA, OFM, V4S maintainers measured in months, not weeks.
-   **Negative:** Adds Node.js + Playwright binary dependency for users who run browser tests.
-   **Risk:** No Playwright end-to-end test passed during the PoC. The 10 ported keywords were validated by static review and selector-strategy analysis only; runtime correctness rests on Phase M1's regex bug fix unlocking E2E execution. **Mitigation:** Phase M1 is small, well-scoped, and runs first; if it surfaces deeper infrastructure problems, the migration plan can be revisited before committing to Phase M2.
-   **Risk:** Sample-size bias — the 10-keyword PoC tested the easy surface. The harder keywords (page object model, form_handlers, label strategy, related-list popups) may surface unforeseen complexity in runtime behaviour, not just selector strategy. **Mitigation:** Phase M2 is structured as ~5 independent PRs, each with its own validation, so the cost gets revealed incrementally rather than as a big-bang surprise.
-   **Risk:** The 3–5× full-port efficiency estimate is calibrated, not measured. **Mitigation:** Phase M2 produces real per-keyword data; we will publish a follow-up ADR (or a supersedes-style update) with the realized numbers once the port is complete.
-   **Risk:** Downstream maintainers may not have capacity to migrate within the deprecation window. **Mitigation:** long deprecation window (≥1 major version + the realized M4 tail), `SalesforceCompat.robot` shim, automated migration tooling, willingness to extend the EOL version if needed.
-   **Risk:** Selenium 4 measurement was a single sample on a single element. **Mitigation:** the qualitative architectural claim (LWC host-chain names are implementation details and as brittle as Aura) generalizes from the host-chain composition, not from the specific 14-statement cost; the decision does not hinge on the precise number.

## References

-   [`docs/adrs/0004-evidence/findings.md`](0004-evidence/findings.md) — Selenium 4 shadow DOM verification, raw measurements, reproduction steps
-   [`docs/adrs/0004-evidence/verify_shadow_dom.py`](0004-evidence/verify_shadow_dom.py) — script that produces the 452 shadow-host count and the host-chain measurement
-   [`docs/adrs/0004-evidence/measure_nesting.py`](0004-evidence/measure_nesting.py) — script that produces the 6-hop depth measurement
-   [`cumulusci/robotframework/locators_66.py`](../../cumulusci/robotframework/locators_66.py) — the 4 Selenium locator overrides for Track A
-   [`cumulusci/robotframework/SalesforcePlaywright.py`](../../cumulusci/robotframework/SalesforcePlaywright.py) — the 10 ported Playwright keywords for Track B (lines 215–337)
-   [`cumulusci/robotframework/Salesforce.py`](../../cumulusci/robotframework/Salesforce.py) — the Selenium keyword surface (~37 keywords) that is the migration target
-   [`cumulusci/robotframework/tests/salesforce/playwright/e2e_comparison.robot`](../../cumulusci/robotframework/tests/salesforce/playwright/e2e_comparison.robot) — the new Playwright E2E test (blocked by Phase M1 bug)
-   [`pyproject.toml`](../../pyproject.toml) — selenium pin (`selenium<4` line 54, `robotframework-seleniumlibrary<6` line 50)
-   [`robotframework-browser` (Playwright)](https://robotframework-browser.org/)
-   [Robot Framework SeleniumLibrary](https://robotframework.org/SeleniumLibrary/)
-   [Selenium 4 shadow DOM API](https://www.selenium.dev/documentation/webdriver/elements/finders/#shadow-dom)
-   [Salesforce Lightning Web Components (LWC)](https://developer.salesforce.com/docs/component-library/documentation/en/lwc)
