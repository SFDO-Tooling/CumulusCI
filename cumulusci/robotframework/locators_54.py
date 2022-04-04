import copy

from cumulusci.robotframework import locators_53

lex_locators = copy.deepcopy(locators_53.lex_locators)
lex_locators["record"]["header"]["field_value"] = (
    "//records-lwc-highlights-panel"
    "//records-highlights-details-item[.//*[contains(@class, 'slds-text-title') and text()='{}']]"
    "//p[contains(@class, 'fieldComponent')]//*[text()]"
)
lex_locators["record"]["header"][
    "field_value_link"
] = "//records-lwc-highlights-panel//records-highlights-details-item[.//*[.='{}']]//a"

lex_locators["modal"][
    "review_alert"
] = "//a[@records-recordediterror_recordediterror and text()='{}']"

lex_locators["list_view_menu"] = {
    "button": "css:button[title='List View Controls']",
    "item": "//div[@title='List View Controls']//ul[@role='menu']//li/a[.='{}']",
}
