import copy

from cumulusci.robotframework import locators_57

lex_locators = copy.deepcopy(locators_57.lex_locators)

# API v66: Actions ribbon migrated from Aura (oneActionsRibbon) to LWC in some
# views (e.g. filtered list views).  The slds-page-header div is in the light
# DOM on all page types and serves as a reliable "page loaded" signal.
lex_locators["actions"] = (
    "//runtime_platform_actions-actions-ribbon//ul"
    "|//ul[contains(concat(' ',normalize-space(@class),' '),' oneActionsRibbon ')]"
    "|//div[contains(@class, 'slds-page-header')]"
)

# API v66: App name changed from nested spans inside div.navLeft to an h1.appName
# element.  Use a broader XPath that matches both old and new structures.
lex_locators["app_launcher"]["current_app"] = (
    "//*[contains(@class,'appName')][.//text()='{}']"
)

# API v66: Related list container migrated from Aura force_relatedListContainer
# to LWC. The count text is now inside a different element structure.
# Use a broader selector that matches both old and new related list layouts.
lex_locators["record"]["related"]["count"] = (
    "//*[@data-component-id='force_relatedListContainer']"
    "//article//span[@title='{0}']/following-sibling::span"
    "|//lst-related-list-single-container"
    "//article//span[@title='{0}']/following-sibling::span"
    "|//article[.//span[@title='{0}']]//span[contains(@class,'countText')]"
)

# API v66: List View Controls button moved into LWC shadow DOM on some page
# types (e.g. filtered list views). Selenium 3 cannot pierce shadow DOM.
# The CSS fallback below works only when the button is in light DOM; shadow DOM
# occurrences are a known, unfixable limitation of the Selenium approach.
lex_locators["list_view_menu"]["button"] = (
    "css:button[title='List View Controls'],button[aria-label='List View Controls']"
)
