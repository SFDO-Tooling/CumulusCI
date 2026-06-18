"""
Measure the shadow DOM nesting depth for the List View Controls button.

This determines whether Selenium 4's WebElement.shadow_root API can practically
reach the element. If the host is multiple shadow boundaries deep, Selenium 4
needs to chain shadow_root.find_element().shadow_root.find_element() at every
level — verbose but possible IF every intermediate host is findable.
"""

import json
import subprocess
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def get_org_auth():
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
    instance_url, access_token = get_org_auth()
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1024")

    driver = webdriver.Chrome(options=options)

    try:
        frontdoor = f"{instance_url}/secur/frontdoor.jsp?sid={access_token}"
        driver.get(frontdoor)
        time.sleep(3)
        lightning_url = instance_url.replace(
            ".my.salesforce.com", ".lightning.force.com"
        )
        driver.get(f"{lightning_url}/lightning/o/Account/list")
        time.sleep(8)

        # Walk up the shadow DOM tree from the target button to body, recording
        # each shadow boundary crossed.
        js = """
        function findInShadowDom(selector, root = document) {
            const matches = [];
            const all = root.querySelectorAll('*');
            for (const el of all) {
                if (el.matches(selector)) matches.push(el);
                if (el.shadowRoot) matches.push(...findInShadowDom(selector, el.shadowRoot));
            }
            return matches;
        }
        const buttons = findInShadowDom("button[title='List View Controls']");
        if (buttons.length === 0) return { error: 'no button found' };
        const target = buttons[0];

        // Walk parent chain, recording shadow boundaries.
        const path = [];
        let node = target;
        while (node) {
            const parent = node.parentNode;
            if (!parent) break;
            if (parent instanceof ShadowRoot) {
                // Crossed a shadow boundary; jump to the host
                path.push({
                    type: 'shadow_boundary',
                    host: parent.host.tagName.toLowerCase(),
                });
                node = parent.host;
            } else {
                node = parent;
                if (node === document.body) break;
            }
        }

        // Count light-DOM-findable hosts: an LWC host is "findable by Selenium"
        // if it is in light DOM (parent is not a ShadowRoot).
        return {
            shadow_boundaries: path.length,
            host_chain: path,
        };
        """
        result = driver.execute_script(js)
        print("Shadow boundary nesting depth:", result.get("shadow_boundaries"))
        print("Host chain (target → body):")
        for i, h in enumerate(result.get("host_chain", [])):
            print(f"  [{i}] <{h['host']}>")

        # Now test: can Selenium 4 chain shadow_root through the nested hosts?
        # Walk from outermost host inward.
        chain = result.get("host_chain", [])
        outermost = chain[-1]["host"] if chain else None
        if outermost:
            print(f"\nOutermost shadow host: <{outermost}>")
            outer_count = len(driver.find_elements(By.CSS_SELECTOR, outermost))
            print(f"  Light DOM matches for <{outermost}>: {outer_count}")

            if outer_count == 0:
                print("  [VERDICT] Outermost host itself is NOT findable in light DOM.")
                print(
                    "  Selenium 4 WebElement.shadow_root API requires the host to be "
                    "found via find_element first, which requires light DOM presence."
                )
                print(
                    "  Therefore: Selenium 4 CANNOT reach this element through the "
                    "documented shadow_root API."
                )
            else:
                print(
                    "  Outermost host IS in light DOM. Selenium 4 chained "
                    "shadow_root traversal would require "
                    f"{result['shadow_boundaries']} hops."
                )

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
