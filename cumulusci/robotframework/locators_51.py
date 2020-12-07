from cumulusci.robotframework import locators_50
import copy

lex_locators = copy.deepcopy(locators_50.lex_locators)

lex_locators["modal"][
    "button"
] = "//div[contains(@class,'uiModal')]//force-form-footer//button[.='{}']"
