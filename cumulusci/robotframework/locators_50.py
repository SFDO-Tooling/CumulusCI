from cumulusci.robotframework import locators_49
import copy

lex_locators = copy.deepcopy(locators_49.lex_locators)

lex_locators["object"][
    "button"
] = "//div[contains(@class, 'slds-page-header')]//*[self::a[@title='{title}'] or self::button[@name='{title}']]"

lex_locators["record"]["header"][
    "field_value_link"
] = "//records-lwc-highlights-panel//force-highlights-details-item[.//*[.='{}']]//a"
