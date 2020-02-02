from cumulusci.robotframework import locators_47

lex_locators = locators_47.lex_locators.copy()

lex_locators["record"]["header"]["field_value"] = (
    "//records-lwc-highlights-panel"
    "//force-highlights-details-item"
    "[.//*[contains(@class, 'slds-text-title') and text()='{}']]"
    "//p[contains(@class, 'fieldComponent')]//*[text()]"
)

lex_locators["record"]["header"]["field_value_link"] = (
    "//records-lwc-highlights-panel"
    "//force-highlights-details-item"
    "[.//*[contains(@class, 'slds-text-title') and text()='{}']]"
    "//p[contains(@class, 'fieldComponent')]//a[text()]"
)

lex_locators["record"]["related"]["link"] = (
    "//article[contains(@class, 'forceRelatedListCardDesktop')]"
    "[.//img]"
    "[.//span[@title='{}']]"
    "//*[text()='{}']"
)

lex_locators["app_launcher"]["menu"] = "//div[contains(@class, 'appLauncherMenu')]"
lex_locators["app_launcher"]["view_all"] = (
    "//div[contains(@class, 'appLauncherMenu')]" "//button[text()='View All']"
)
lex_locators["app_launcher"][
    "app_link"
] = "//one-app-launcher-modal//one-app-launcher-app-tile//a[.='{}']"
lex_locators["app_launcher"][
    "tab_link"
] = "//one-app-launcher-modal//one-app-launcher-tab-item//a[.='{}']"

lex_locators["object"]["field_lookup_link"] = "//*[@role='option'][.//*[@title='{}']]"

# NPSP tests were failing because the New Opportunity modal no longer
# is using the class modal-footer.
lex_locators["modal"]["button"] = (
    "//div[contains(@class,'uiModal')]"
    "//div[contains(@class, 'modal-footer') or contains(@class, 'inlineFooter')]"
    # I don't like using an '*' here, but the link might be an <a> or it
    # might be a <span>.
    "//button[.//*[text()='{}']]"
)
