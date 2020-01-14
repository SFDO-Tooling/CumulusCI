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
