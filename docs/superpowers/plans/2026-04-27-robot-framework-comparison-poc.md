# Robot Framework Maintenance Comparison PoC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compare agent-maintained Selenium locator refresh against a focused Playwright keyword port for CumulusCI Robot Framework maintenance, backed by tests and an ADR.

**Architecture:** Two parallel tracks against the same scratch org (API v66). Track A refreshes `locators_66.py` and fixes inline locator breakage across page objects. Track B ports ~8 keywords to `SalesforcePlaywright.py` and runs one end-to-end test. Both tracks feed into a comparison analysis and ADR 0004.

**Tech Stack:** Python 3.13, Robot Framework, Selenium 3, Playwright/rfbrowser, CumulusCI (via `uv run cci`), headlesschrome

---

## File Map (Before Tasks)

**Track A (Selenium locator refresh)**

-   WIP: `cumulusci/robotframework/locators_66.py` (3 overrides done)
-   WIP: `cumulusci/robotframework/tests/salesforce/TestLibraryA.py` (breadcrumb fix done)
-   WIP: `cumulusci/robotframework/tests/salesforce/locators.robot` (Object Manager fix done)
-   May modify: `cumulusci/robotframework/pageobjects/BasePageObjects.py` (inline `uiModal` locators)
-   May modify: `cumulusci/robotframework/pageobjects/ObjectManagerPageObject.py` (standalone locator dict)

**Track B (Playwright keyword port)**

-   Modify: `cumulusci/robotframework/SalesforcePlaywright.py` (add ~8 keywords)
-   Create: `cumulusci/robotframework/tests/salesforce/playwright/e2e_comparison.robot`

**ADR and docs**

-   Create: `docs/adrs/0004-robot-framework-selenium-vs-playwright.md`
-   Create: `~/.cursor/skills-cursor/robot-locator-refresh/SKILL.md` (local only)
-   Modify: `/Users/jestevez/.cursor/plans/cumulusci_development_restart_f991bc4b.plan.md`

---

### Task 1: Finish Track A Locators — Verify forms.robot and Run Full Battery

**Files:**

-   Test: `cumulusci/robotframework/tests/salesforce/forms.robot`
-   May modify: `cumulusci/robotframework/locators_66.py`

-   [ ] **Step 1: Re-run forms.robot to test the list_view_menu.button fix**

Run:

```bash
uv run cci task run robot --org robot-poc -o suites cumulusci/robotframework/tests/salesforce/forms.robot -o vars BROWSER:headlesschrome
```

Expected: 6/6 pass, OR the "Lightning based form - radiobutton" test fails due to shadow DOM. If it fails, document the failure message.

-   [ ] **Step 2: If radiobutton test fails, document as shadow DOM limitation**

If the test at line 106 of `forms.robot` fails because `sf:list_view_menu.button` cannot be found (element is inside LWC shadow DOM), add a comment to `locators_66.py`:

```python
# KNOWN LIMITATION: list_view_menu.button is inside LWC shadow DOM on some
# page types (e.g. filtered list views). Selenium 3 cannot pierce shadow DOM.
# The CSS fallback works only when the button is in light DOM.
```

-   [ ] **Step 3: Run the full 11-suite Selenium battery**

Run:

```bash
uv run cci task run robot --org robot-poc -o suites cumulusci/robotframework/tests/salesforce/api.robot,cumulusci/robotframework/tests/salesforce/browsers.robot,cumulusci/robotframework/tests/salesforce/classic.robot,cumulusci/robotframework/tests/salesforce/create_contact.robot,cumulusci/robotframework/tests/salesforce/faker.robot,cumulusci/robotframework/tests/salesforce/forms.robot,cumulusci/robotframework/tests/salesforce/label_locator.robot,cumulusci/robotframework/tests/salesforce/locators.robot,cumulusci/robotframework/tests/salesforce/performance.robot,cumulusci/robotframework/tests/salesforce/populate.robot,cumulusci/robotframework/tests/salesforce/ui.robot -o vars BROWSER:headlesschrome
```

Expected: all pass except possibly the forms.robot radiobutton test (shadow DOM). Record exact pass/fail counts.

-   [ ] **Step 4: Fix any new failures discovered in the full battery**

For each failure: inspect the error, update `locators_66.py` with a corrected locator, re-run the failing suite to confirm.

-   [ ] **Step 5: Commit Track A locator work**

```bash
git add cumulusci/robotframework/locators_66.py cumulusci/robotframework/tests/salesforce/TestLibraryA.py cumulusci/robotframework/tests/salesforce/locators.robot
git commit -m "feat(robot): add locators_66.py for API v66 with Selenium locator refresh

Three locator overrides for API v66 DOM changes plus test assertion
updates for Object Manager and breadcrumb navigation."
```

---

### Task 2: Track A Page Objects — Run and Fix Inline Locator Breakage

**Files:**

-   Test: `cumulusci/robotframework/tests/salesforce/pageobjects/base_pageobjects.robot`
-   Test: `cumulusci/robotframework/tests/salesforce/pageobjects/listing_page.robot`
-   Test: `cumulusci/robotframework/tests/salesforce/pageobjects/objectmanager.robot`
-   Test: `cumulusci/robotframework/tests/salesforce/pageobjects/pageobjects.robot`
-   May modify: `cumulusci/robotframework/pageobjects/BasePageObjects.py`
-   May modify: `cumulusci/robotframework/pageobjects/ObjectManagerPageObject.py`

-   [ ] **Step 1: Run the 4 page object suites**

Run:

```bash
uv run cci task run robot --org robot-poc -o suites cumulusci/robotframework/tests/salesforce/pageobjects/base_pageobjects.robot,cumulusci/robotframework/tests/salesforce/pageobjects/listing_page.robot,cumulusci/robotframework/tests/salesforce/pageobjects/objectmanager.robot,cumulusci/robotframework/tests/salesforce/pageobjects/pageobjects.robot -o vars BROWSER:headlesschrome
```

Expected: some may fail due to inline locators referencing `uiModal` (Aura class) or Object Manager page structure changes.

-   [ ] **Step 2: For each failure, identify whether it's an inline locator issue**

Check the error against the known inline locators in `BasePageObjects.py`:

-   Line 119, 244, 264: `//div[contains(@class, 'uiModal')]`
-   Line 275: `//label[text()="..."]`
-   Line 287: `.//*[contains(@class, 'slds-form-element')...]`

And in `ObjectManagerPageObject.py`:

-   Lines 6-20: standalone `object_manager` dict

-   [ ] **Step 3: Fix any broken inline locators**

Update the inline locators in the affected files. Prefer SLDS/Lightning-stable selectors. For `uiModal`, check if the modal is now using `slds-modal` instead.

-   [ ] **Step 4: Re-run page object suites to verify fixes**

Run same command as Step 1. Expected: all pass, or failures documented as shadow DOM limitations.

-   [ ] **Step 5: Commit page object fixes**

```bash
git add -A cumulusci/robotframework/pageobjects/
git commit -m "fix(robot): update inline locators in page objects for API v66

Fix inline locators in BasePageObjects.py and ObjectManagerPageObject.py
that bypass the versioned lex_locators system."
```

---

### Task 3: Track A Audit — Locator Durability Analysis

**Files:**

-   Read: `cumulusci/robotframework/locators_66.py`
-   Read: `cumulusci/robotframework/locators_56.py`

-   [ ] **Step 1: Count Aura-internal references in locators_66.py**

Search for these Aura-internal patterns in the final `locators_66.py` (after inheriting from 57/56):

-   `uiModal`
-   `oneActionsRibbon`
-   `auraLoadingBox`
-   `forceListViewManager`
-   `data-aura-rendered-by`
-   `data-aura-class`
-   `uiInput`
-   `uiLabel`
-   `uiPopupTarget`
-   `forceFormPageError`
-   `force_relatedListContainer` (data-component-id)

Record the count and which locator keys use them.

-   [ ] **Step 2: Count SLDS/Lightning-stable references**

Search for:

-   `slds-*` class patterns
-   `lightning-*` element names
-   Standard ARIA attributes (`role=`, `title=`, `aria-label=`)

Record the count.

-   [ ] **Step 3: Diff locators_66.py against locators_56.py**

Run:

```bash
python3 -c "
from cumulusci.robotframework import locators_56, locators_66
import json

def flatten(d, prefix=''):
    items = []
    for k, v in d.items():
        key = f'{prefix}.{k}' if prefix else k
        if isinstance(v, dict):
            items.extend(flatten(v, key))
        else:
            items.append((key, v))
    return items

old = dict(flatten(locators_56.lex_locators))
new = dict(flatten(locators_66.lex_locators))
changed = {k: (old[k], new[k]) for k in old if k in new and old[k] != new[k]}
added = {k: new[k] for k in new if k not in old}
removed = {k: old[k] for k in old if k not in new}
print(f'Changed: {len(changed)}')
for k, (o, n) in changed.items():
    print(f'  {k}')
print(f'Added: {len(added)}')
print(f'Removed: {len(removed)}')
print(f'Unchanged: {len(old) - len(changed) - len(removed)}')
"
```

Expected: small number of changes (currently 3 overrides).

-   [ ] **Step 4: Write the audit summary as a text file for ADR reference**

Create a brief markdown summary with the counts. Save as a local note (not committed — this feeds into the ADR and comparison).

---

### Task 4: Draft Local Skill Spec

**Files:**

-   Create: `~/.cursor/skills-cursor/robot-locator-refresh/SKILL.md`

-   [ ] **Step 1: Write the skill spec**

The skill spec should contain:

-   **Inputs**: CCI org alias, test suite path, target API version
-   **Process**: copy-on-write from previous locator version, run test suites, fix failures, audit results
-   **Best practices checklist**: no hardcoded strings, minimal XPath, parameterized format strings, no positional indexes, `@selenium_retry` on Selenium keywords, minimal `sleep`, prefer SLDS/Lightning selectors over Aura internals
-   **Locator failure vs application bug**: how to distinguish (locator not found = locator issue; element found but wrong behavior = app bug)
-   **Output**: diff of locator changes + summary

-   [ ] **Step 2: Verify the skill file is at the correct path**

```bash
ls -la ~/.cursor/skills-cursor/robot-locator-refresh/SKILL.md
```

Expected: file exists with reasonable content.

---

### Task 5: Track B — Port Playwright Keywords

**Files:**

-   Modify: `cumulusci/robotframework/SalesforcePlaywright.py`

-   [ ] **Step 1: Read existing SalesforcePlaywright.py and understand current keywords**

Current keywords (8): `get_current_record_id`, `go_to_record_home`, `delete_records_and_close_browser`, `open_test_browser`, `wait_until_loading_is_complete`, `wait_until_salesforce_is_ready`, `_check_for_classic`, `breakpoint`.

-   [ ] **Step 2: Add app launcher keywords**

Add to `SalesforcePlaywright.py`:

-   `open_app_launcher` — click the waffle button, wait for the app launcher modal
-   `select_app_launcher_app` — type in the search field, click the matching app tile
-   `select_app_launcher_tab` — type in the search field, click the matching tab item

Use Playwright accessibility selectors: `role=button[name="App Launcher"]`, `role=dialog`, `role=option`, `text=` selectors.

-   [ ] **Step 3: Add form keywords**

Add:

-   `populate_field` — find label, locate associated input, fill value using Playwright's `fill()` or `type_text()`
-   `populate_form` — iterate key=value pairs, call `populate_field` for each

Use Playwright's `label:` selector strategy and `fill()` for replacement semantics.

-   [ ] **Step 4: Add modal keywords**

Add:

-   `click_modal_button` — find button within modal dialog by text
-   `wait_until_modal_is_open` — wait for `div.slds-modal` to be visible
-   `wait_until_modal_is_closed` — wait for `div.slds-modal` to not be visible (or use Playwright's `wait_for_selector(state="hidden")` equivalent)

-   [ ] **Step 5: Add related list keywords**

Add:

-   `click_related_list_button` — find the related list card by title, click button within it
-   `get_related_list_count` — find the count span next to the related list title

-   [ ] **Step 6: Run existing Playwright tests to verify no regressions**

Run:

```bash
uv run cci task run robot --org robot-poc -o suites cumulusci/robotframework/tests/salesforce/playwright/ -o vars BROWSER:headlesschrome
```

Expected: existing 4 Playwright suites still pass (or pre-existing failures unchanged).

-   [ ] **Step 7: Commit Track B keyword port**

```bash
git add cumulusci/robotframework/SalesforcePlaywright.py
git commit -m "feat(robot): port ~8 Playwright keywords for comparison PoC

Add app launcher, form, modal, and related list keywords to
SalesforcePlaywright.py using Playwright accessibility selectors."
```

---

### Task 6: Track B — Write and Run End-to-End Playwright Test

**Files:**

-   Create: `cumulusci/robotframework/tests/salesforce/playwright/e2e_comparison.robot`

-   [ ] **Step 1: Write the end-to-end test**

```robot
*** Settings ***
Resource         cumulusci/robotframework/SalesforcePlaywright.robot

Suite Setup      Open test browser
Suite Teardown   Delete records and close browser

Force Tags       playwright

*** Test Cases ***
Create contact via app launcher and verify
    Open app launcher
    Select app launcher app    Sales
    Wait until loading is complete

    Go to object home    Contact

    # Create a new contact
    Click    button:has-text("New")
    Wait until modal is open

    Populate form
    ...    First Name=Test
    ...    Last Name=RobotPlaywright

    Click modal button    Save
    Wait until modal is closed
    Wait until loading is complete

    # Verify we landed on the record page
    Get current record id
```

-   [ ] **Step 2: Run the test**

Run:

```bash
uv run cci task run robot --org robot-poc -o suites cumulusci/robotframework/tests/salesforce/playwright/e2e_comparison.robot -o vars BROWSER:headlesschrome
```

Expected: test passes. If it fails, iterate on keyword implementations.

-   [ ] **Step 3: Fix any failures and re-run**

Adjust keyword implementations in `SalesforcePlaywright.py` or test selectors in the `.robot` file based on actual DOM structure.

-   [ ] **Step 4: Commit the test**

```bash
git add cumulusci/robotframework/tests/salesforce/playwright/e2e_comparison.robot
git commit -m "test(robot): add Playwright e2e comparison test

End-to-end test exercising app launcher, form, modal, and record
verification via SalesforcePlaywright keywords."
```

---

### Task 7: Comparison Analysis

**Files:**

-   Read: audit results from Task 3
-   Read: test results from Tasks 1, 2, 5, 6

-   [ ] **Step 1: Gather token cost approximation**

Estimate token cost per track from conversation length:

-   Track A: messages/tokens consumed for locator refresh (Tasks 1-3)
-   Track B: messages/tokens consumed for Playwright port (Tasks 5-6)

-   [ ] **Step 2: Compile comparison table**

| Metric                           | Track A (Selenium) | Track B (Playwright) |
| -------------------------------- | ------------------ | -------------------- |
| Token cost (approx)              |                    |                      |
| Locator changes needed           |                    |                      |
| Aura-internal refs remaining     |                    |                      |
| Shadow DOM blockers              |                    |                      |
| Keywords covered                 | 37 (full)          | ~8 (ported)          |
| Per-release maintenance estimate |                    |                      |

-   [ ] **Step 3: Assess per-release maintenance posture**

For Track A: how much of the work was mechanical (copy locator file, run tests, fix failures) vs. requiring deep DOM investigation?

For Track B: how many keywords needed no locator changes at all (because Playwright's accessibility selectors are version-independent)?

---

### Task 8: Write ADR 0004

**Files:**

-   Create: `docs/adrs/0004-robot-framework-selenium-vs-playwright.md`

-   [ ] **Step 1: Write the ADR following the template**

Use the template from `docs/adrs/templates/template.md`. Sections:

-   **Context and Problem Statement**: CCI's Robot Framework tests use Selenium 3 with versioned locators. Per-release locator maintenance stopped. Agent-era token budgets change the calculus. Shadow DOM migration creates a structural ceiling for Selenium.
-   **Assumptions**: agent tokens are abundant; Salesforce continues Aura-to-LWC migration; downstream consumers (NPSP/EDA) need migration path.
-   **Constraints**: Selenium 3 cannot pierce shadow DOM; `robotframework-browser` requires separate install; backward compatibility with existing `sf:` locator prefix consumers.
-   **Considered Options**: (1) Selenium-only with agent-maintained locators, (2) Playwright-only with full migration, (3) Dual-track: maintain Selenium for backward compat, develop new tests in Playwright.
-   **Decision Outcome**: based on comparison evidence.
-   **Consequences**: what changes for downstream consumers, what maintenance commitments are made.

Set `status: Proposed`, `date: 2026-04-27`.

-   [ ] **Step 2: Commit the ADR**

```bash
git add -f docs/adrs/0004-robot-framework-selenium-vs-playwright.md
git commit -m "docs: add ADR 0004 Robot Framework Selenium vs Playwright

Evidence-backed ADR from dual-track comparison PoC comparing
agent-maintained Selenium locator refresh against Playwright port."
```

---

### Task 9: Update Parent Roadmap

**Files:**

-   Modify: `/Users/jestevez/.cursor/plans/cumulusci_development_restart_f991bc4b.plan.md`

-   [ ] **Step 1: Read current roadmap state**

Read the file and identify:

-   Frontmatter todos `adr-robot-playwright` and `robot-locator-refresh-poc`
-   Body sections for Robot Framework phases
-   "Suggested merge-to-dev sequence" Merge E entry
-   "Current State" section
-   "Consolidated from" line

-   [ ] **Step 2: Update frontmatter todos**

Set `adr-robot-playwright` to `completed` with summary of ADR outcome.
Set `robot-locator-refresh-poc` to `completed` with locator audit numbers and skill spec status.

-   [ ] **Step 3: Rewrite body sections**

Replace "Phase: Robot Framework and Playwright -- ADR Required" evidence-first subsection with actual evidence and ADR conclusion.
Replace "Phase: Agent-Driven Locator Refresh (Proof of Concept)" with results summary.

-   [ ] **Step 4: Reconcile Merge E**

Replace the stale "ADR: Robot Framework maintenance mode, deprecate Playwright tech preview ... No code changes -- policy decision only" with the actual merge structure used.

-   [ ] **Step 5: Refresh Current State if needed**

Update date and summary if the PoC outcome materially changes the v5 trajectory.

-   [ ] **Step 6: Add session reference to Consolidated from line**

Append this chat's reference to the existing line.
