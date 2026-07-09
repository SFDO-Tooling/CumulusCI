"""
Selenium 4 shadow DOM piercing verification against the robot-poc scratch org.

Goal: Verify whether Selenium 4's shadow_root API can reach
`list_view_menu.button` (the "List View Controls" gear) on a filtered list view,
which Selenium 3 cannot find.

Authenticates via Salesforce frontdoor URL using the access token from
sf cli, navigates to the Account list view (which is where forms.robot runs
the failing radiobutton test), and attempts multiple shadow DOM piercing
strategies.
"""

import json
import subprocess
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def get_org_auth():
    """Get instance URL and access token from sf cli."""
    result = subprocess.run(
        [
            "sf",
            "org",
            "display",
            "--target-org",
            "test-0frwzz98ullr@example.com",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)["result"]
    return data["instanceUrl"], data["accessToken"]


def main():
    print("=" * 70)
    print("Selenium 4 Shadow DOM Piercing Verification")
    print("=" * 70)

    instance_url, access_token = get_org_auth()
    print(f"Instance: {instance_url}")
    print(
        f"Selenium: {webdriver.__version__ if hasattr(webdriver, '__version__') else 'unknown'}"
    )

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1024")

    driver = webdriver.Chrome(options=options)

    try:
        # 1. Authenticate via frontdoor
        frontdoor = f"{instance_url}/secur/frontdoor.jsp?sid={access_token}"
        print("\n[1] Authenticating via frontdoor URL...")
        driver.get(frontdoor)
        time.sleep(3)
        print(f"    Landed at: {driver.current_url[:120]}")

        # 2. Switch to Lightning if needed (frontdoor lands on classic for some orgs)
        if (
            "/one/one.app" not in driver.current_url
            and "lightning.force.com" not in driver.current_url
        ):
            print("    Navigating to Lightning home...")
            lightning_url = instance_url.replace(
                ".my.salesforce.com", ".lightning.force.com"
            )
            driver.get(f"{lightning_url}/lightning/page/home")
            time.sleep(5)
            print(f"    Now at: {driver.current_url[:120]}")

        # 3. Navigate to Account list view (same place forms.robot fails)
        lightning_base = driver.current_url.split("/lightning/")[0]
        list_view_url = f"{lightning_base}/lightning/o/Account/list"
        print(f"\n[2] Navigating to Account list view: {list_view_url}")
        driver.get(list_view_url)
        time.sleep(8)
        print(f"    Page title: {driver.title}")

        # 4. Attempt to find list_view_menu.button via Selenium 3 style first
        print("\n[3] Selenium-3 style locator (light DOM only):")
        s3_locator = (
            "//lightning-button-icon[@title='List View Controls']/button"
            "|//*[contains(@class, 'slds-icon-utility-settings')]"
        )
        results = driver.find_elements(By.XPATH, s3_locator)
        print(f"    XPath light-DOM match count: {len(results)}")
        for i, r in enumerate(results[:3]):
            try:
                print(f"    [{i}] tag={r.tag_name}, displayed={r.is_displayed()}")
            except Exception as e:
                print(f"    [{i}] error inspecting: {e}")

        # 5. Try Selenium 3 CSS fallback (the one we used in locators_66.py)
        print("\n[4] Selenium-3 CSS fallback locator:")
        css_locator = (
            "button[title='List View Controls'],button[aria-label='List View Controls']"
        )
        results = driver.find_elements(By.CSS_SELECTOR, css_locator)
        print(f"    Light-DOM CSS match count: {len(results)}")

        # 6. Walk the LWC component tree and look for shadow roots
        print("\n[5] Walking shadow DOM tree:")
        # The list view Lightning component is `lst-related-list-view-manager` /
        # `force-list-view-manager` etc. depending on version. Let's just find ALL
        # shadow hosts and check if any contain "List View Controls".
        js_search = """
        function findInShadowDom(selector, root = document) {
            const matches = [];
            const all = root.querySelectorAll('*');
            for (const el of all) {
                if (el.matches(selector)) matches.push(el);
                if (el.shadowRoot) {
                    matches.push(...findInShadowDom(selector, el.shadowRoot));
                }
            }
            return matches;
        }
        const matches = findInShadowDom(
            "button[title='List View Controls'], button[aria-label='List View Controls'], button[name='showListViewActions']"
        );
        return matches.map(m => ({
            tag: m.tagName.toLowerCase(),
            title: m.getAttribute('title'),
            ariaLabel: m.getAttribute('aria-label'),
            name: m.getAttribute('name'),
            inShadow: m.getRootNode() !== document,
            shadowHost: m.getRootNode() !== document ? m.getRootNode().host?.tagName?.toLowerCase() : null,
        }));
        """
        all_buttons = driver.execute_script(js_search)
        print(f"    Total matches across all DOM levels: {len(all_buttons)}")
        for i, b in enumerate(all_buttons[:5]):
            print(
                f"    [{i}] tag={b['tag']} title={b['title']!r} "
                f"in_shadow={b['inShadow']} shadow_host={b['shadowHost']}"
            )

        # 7. Now use Selenium 4 shadow_root API to navigate to one of them
        print("\n[6] Selenium 4 shadow_root API access attempt:")
        if all_buttons and any(b["inShadow"] for b in all_buttons):
            shadow_targets = [b for b in all_buttons if b["inShadow"]]
            print(
                f"    Found {len(shadow_targets)} shadow-DOM-only matches. "
                f"Testing Selenium 4 traversal..."
            )

            # Find shadow hosts that contain List View Controls
            host_tag = shadow_targets[0]["shadowHost"]
            print(f"    Targeting shadow host: <{host_tag}>")

            try:
                hosts = driver.find_elements(By.CSS_SELECTOR, host_tag)
                print(f"    Shadow host element count: {len(hosts)}")
                pierced = 0
                for h in hosts:
                    try:
                        sr = h.shadow_root
                        try:
                            inner = sr.find_element(
                                By.CSS_SELECTOR,
                                "button[title='List View Controls']",
                            )
                            print(
                                f"    [SUCCESS] Pierced shadow root via "
                                f"WebElement.shadow_root, found inner button: "
                                f"tag={inner.tag_name}"
                            )
                            pierced += 1
                            break
                        except Exception:
                            continue
                    except Exception:
                        # Some elements may not be shadow hosts
                        continue
                if pierced == 0:
                    print(
                        "    [PARTIAL] shadow_root accessible but inner button "
                        "not found in expected host"
                    )
            except Exception as e:
                print(f"    [FAIL] {type(e).__name__}: {e}")
        elif all_buttons:
            print("    Button(s) found in light DOM, no shadow DOM piercing needed.")
        else:
            print("    [CAVEAT] No List View Controls button found anywhere on page.")
            print("    The element may only render after a list view is selected.")

        # 8. As an additional data point: count shadow roots present
        shadow_count = driver.execute_script(
            """
            let count = 0;
            const walker = document.createTreeWalker(document, NodeFilter.SHOW_ELEMENT);
            let node;
            while ((node = walker.nextNode())) {
                if (node.shadowRoot) count++;
            }
            return count;
            """
        )
        print(f"\n[7] Total shadow roots on this page: {shadow_count}")

        print("\n" + "=" * 70)
        print("VERIFICATION COMPLETE")
        print("=" * 70)

    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main() or 0)
