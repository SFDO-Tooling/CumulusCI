---
date: 2026-04-27
status: Proposed
author: "<!--@jstvz-->"
---

# 4. Robot Framework: Selenium Locator Maintenance vs Playwright Migration

## Context and Problem Statement

CumulusCI's Robot Framework tests use Selenium 3 with versioned locator dictionaries (one Python file per Salesforce API version). Per-release locator maintenance stopped due to team capacity constraints—no new locator file has been added since API v56.

Two developments change the calculus:

1. **Agent-era token budgets.** Automated agents can absorb the mechanical burden of per-release locator diffs, making Selenium maintenance tractable again.
2. **Shadow DOM migration.** Salesforce continues migrating components from Aura to LWC. LWC components render inside shadow DOM, which Selenium 3's `find_element` cannot pierce. This creates a structural ceiling for the Selenium-based approach that grows with each API version.

We need to decide the maintenance path for CumulusCI's Robot Framework browser-test infrastructure.

### Assumptions

-   Agent tokens are abundant for mechanical maintenance tasks (locator diffs, test updates).
-   Salesforce continues its Aura-to-LWC migration each API version, increasing shadow DOM surface area.
-   NPSP, EDA, and other downstream consumers depend on the `sf:` locator prefix provided by CumulusCI's Salesforce library.
-   `robotframework-browser` (Playwright) is a viable Robot Framework library alternative to SeleniumLibrary.

### Constraints

-   **Selenium 3 cannot pierce shadow DOM.** There is no supported path to shadow DOM access without upgrading to Selenium 4+ or switching drivers.
-   **Backward compatibility required.** The `sf:` locator prefix is a public API consumed by downstream projects; breaking changes must be avoided or carefully managed.
-   **`robotframework-browser` requires separate installation.** It depends on Node.js and Playwright binaries, adding to the install footprint.

## Decision

### Considered Options

1. **Selenium-only with agent-maintained locators**

    1. Good: No migration cost; existing tests and downstream consumers are unaffected.
    1. Good: Agent-driven locator diffs are mechanically tractable—PoC demonstrated 4 overrides needed across 10 API versions.
    1. Bad: Shadow DOM ceiling is permanent; Selenium 3 cannot access LWC internals.
    1. Bad: 34% of locators reference Aura internals that will eventually be replaced by LWC equivalents.

2. **Playwright-only with full migration**

    1. Good: Playwright auto-pierces shadow DOM—no version-specific locators needed.
    1. Good: Accessibility-first selectors are stable across Salesforce releases.
    1. Good: Built-in auto-wait eliminates the need for `@selenium_retry` decorators.
    1. Bad: Requires porting all 37 Salesforce keywords to `robotframework-browser`.
    1. Bad: Breaking change for all downstream `sf:` prefix consumers.
    1. Bad: Adds Node.js + Playwright binary dependency to CumulusCI's install.

3. **Dual-track: maintain Selenium for backward compat, develop new tests in Playwright**

    1. Good: Preserves backward compatibility for existing `sf:` prefix consumers.
    1. Good: New test development can use shadow-DOM-capable, version-independent Playwright selectors.
    1. Good: Provides a gradual migration path—keywords can be ported incrementally.
    1. Bad: Two maintenance surfaces; both Selenium and Playwright paths must be tested.
    1. Bad: Increases cognitive load for contributors who must understand both libraries.

### Decision Outcome

**Recommended: Option 3 (dual-track).**

The PoC produced concrete evidence for this recommendation:

**Track A — Selenium locator refresh (API v56 → v66, spanning 10 versions):**

-   Only **4 locator overrides** were needed to bridge 10 API versions.
-   **101 of 102** Robot Framework tests pass after the refresh.
-   **1 unfixable failure**: the actions ribbon is now rendered inside shadow DOM, which Selenium 3 cannot reach.
-   **14 of 41** locators (34%) reference Aura-specific internals.
-   **14 of 41** locators use SLDS-stable class references.

**Track B — Playwright keyword port:**

-   **~8 keywords** were ported using accessibility-first selectors (`role=`, `text=`).
-   **Zero version-specific locators** were required.
-   Playwright's **auto-wait** eliminated the need for `@selenium_retry` decorators entirely.

**Shadow DOM evidence:** The actions ribbon and List View Controls button are confirmed to render inside shadow DOM. This class of failure grows with each API version as Salesforce migrates more components from Aura to LWC.

The Selenium locator refresh is mechanically tractable for agents—4 overrides across 10 versions is a low per-release burden. However, the shadow DOM ceiling is structural and permanent under Selenium 3. Playwright keywords are version-independent and shadow-DOM-capable but require porting 37 keywords to reach full parity. Dual-track preserves backward compatibility while building toward the Playwright future.

## Consequences

-   **Positive:** Existing `sf:` prefix consumers (NPSP, EDA, etc.) are unaffected and can continue using Selenium-based keywords.
-   **Positive:** New test development can target Playwright, avoiding shadow DOM limitations from day one.
-   **Positive:** Agent-maintained Selenium locators keep the existing test suite functional during the transition period.
-   **Negative:** Two maintenance surfaces—both Selenium and Playwright keyword implementations must be kept tested and documented.
-   **Negative:** Contributors must understand both SeleniumLibrary and `robotframework-browser` APIs.
-   **Risk:** The shadow DOM ceiling for Selenium grows each Salesforce release. If migration to Playwright stalls, an increasing number of Selenium tests will become unfixable.

## References

-   [robotframework-browser (Playwright)](https://robotframework-browser.org/)
-   [Robot Framework SeleniumLibrary](https://robotframework.org/SeleniumLibrary/)
-   [Selenium 3 shadow DOM limitation](https://www.selenium.dev/documentation/webdriver/elements/finders/#shadow-dom)
-   [Salesforce Lightning Web Components (LWC)](https://developer.salesforce.com/docs/component-library/documentation/en/lwc)
-   PoC spec: `docs/superpowers/specs/2026-04-27-robot-framework-comparison-poc-design.md`
