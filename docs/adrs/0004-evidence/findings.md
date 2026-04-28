# Selenium 4 Shadow DOM Verification — Findings

**Date:** 2026-04-27
**Org:** `robot-poc` scratch (API v66, instance USA882S)
**Page tested:** `/lightning/o/Account/list` (the same page where `forms.robot::Lightning based form - radiobutton` fails)
**Element targeted:** `button[title='List View Controls']` (the `sf:list_view_menu.button` locator that fails in `forms.robot`)

## Setup

-   Isolated venv at `/tmp/selenium4-poc/` with `selenium==4.43.0` and headless Chrome.
-   Authenticated via Salesforce frontdoor URL (`/secur/frontdoor.jsp?sid=<access_token>`).
-   Two scripts: [`verify_shadow_dom.py`](verify_shadow_dom.py) (overall capability) and [`measure_nesting.py`](measure_nesting.py) (depth measurement).

## Measurements

| Measurement                                                    | Value                                                                                                                                                                       |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shadow roots present on the page                               | **452**                                                                                                                                                                     |
| Selenium 3 XPath/CSS matches for the target button (light DOM) | **0**                                                                                                                                                                       |
| Shadow boundary depth from button to `<body>`                  | **6 hops**                                                                                                                                                                  |
| Host chain (button → outer)                                    | `lightning-button-menu` → `lst-list-view-manager-settings-menu` → `lst-list-view-manager-header` → `lst-common-list-internal` → `lst-list-view-manager` → `lst-object-home` |
| Outermost host (`lst-object-home`) findable in light DOM?      | **Yes (1 match)**                                                                                                                                                           |
| Selenium 4 chained `shadow_root` traversal feasible?           | Yes, but requires **7 `find_element` + 6 `shadow_root` accesses** (~14 lines of Python per element)                                                                         |
| Playwright equivalent                                          | `page.get_by_role("button", name="List View Controls").click()` — 1 line, auto-pierces all 6 boundaries                                                                     |

## Implications

1. **Selenium 3 cannot reach the element.** Confirmed: 0 matches via XPath or CSS in the light DOM.
2. **Selenium 4 can technically reach it,** because the outermost shadow host is in light DOM. But it requires manual chaining through 6 boundaries with internal LWC component names (`lst-*`).
3. **The host chain contains LWC-internal names.** Names like `lst-list-view-manager-settings-menu` are SLDS implementation details and likely to be renamed across API versions. Each rename = locator break in the same way Aura `force_*` classes break today.
4. **Playwright auto-pierces shadow DOM** at any depth, using accessibility-tree selectors that map to the public ARIA contract — meaningfully more stable than internal LWC component names.

## Cost ratio for shadow-DOM-bound elements

| Path                                                | Lines per element | Stability of selectors                  | Per-version maintenance        |
| --------------------------------------------------- | ----------------- | --------------------------------------- | ------------------------------ |
| Selenium 3 (current)                                | N/A — unfixable   | N/A                                     | Growing failures every release |
| Selenium 4 chained traversal                        | ~14               | LWC-internal names (brittle, like Aura) | Per-release rewrites likely    |
| Playwright (`get_by_role`, `text=`, `data-testid=`) | 1                 | ARIA / SLDS public contract             | Near-zero                      |

For the Account list view alone, with 452 shadow roots, anything that depends on a shadow-DOM-bound element pays this 14× verbosity tax under Selenium 4.

## Reproducibility

```bash
# In a clean tmpdir
uv venv .venv --python 3.13
uv pip install --python ./.venv 'selenium>=4'
./.venv/bin/python verify_shadow_dom.py
./.venv/bin/python measure_nesting.py
```

Requires `sf` CLI authenticated against an org alias and the script edited to point at it.
