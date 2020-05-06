from cumulusci.robotframework import locators_48
import copy

lex_locators = copy.deepcopy(locators_48.lex_locators)

lex_locators["app_launcher"][
    "button"
] = "//div[contains(@class,'appLauncher')]//button[//div[contains(@class,'slds-icon-waffle')]]"
