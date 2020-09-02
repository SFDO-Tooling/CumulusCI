from cumulusci.robotframework import locators_49
import copy

lex_locators = copy.deepcopy(locators_49.lex_locators)

lex_locators["actions"] = (
    "//runtime_platform_actions-actions-ribbon//ul"
    "|"
    "//ul[contains(concat(' ',normalize-space(@class),' '),' oneActionsRibbon ')]"
)

lex_locators["object"][
    "button"
] = "//div[contains(@class, 'slds-page-header')]//*[self::a[@title='{title}'] or self::button[@name='{title}']]"

lex_locators["record"]["header"][
    "field_value_link"
] = "//records-lwc-highlights-panel//force-highlights-details-item[.//*[.='{}']]//a"


lex_locators["record"]["related"] = {
    "button": "//*[@data-component-id='force_relatedListContainer']//article[.//span[@title='{}']]//a[@title='{}']",
    "card": "//*[@data-component-id='force_relatedListContainer']//article[.//span[@title='{}']]",
    "count": "//*[@data-component-id='force_relatedListContainer']//article//span[@title='{}']/following-sibling::span",
    "link": "//*[@data-component-id='force_relatedListContainer']//article[.//span[@title='{}']]//*[text()='{}']",
    "popup_trigger": "//*[@data-component-id='force_relatedListContainer']//article[.//span[@title='{}']]//span[text()='Show Actions']",
}
