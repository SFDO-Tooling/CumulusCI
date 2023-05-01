from cumulusci.robotframework import locators_50
import copy

lex_locators = copy.deepcopy(locators_50.lex_locators)

lex_locators["modal"][
    "button"
] = "//div[contains(@class,'uiModal')]//force-form-footer//button[.='{}']"

lex_locators["modal"]["has_error"] = "css: div.forceFormPageError"

lex_locators["modal"][
    "review_alert"
] = '//a[@force-recordediterror_recordediterror and text()="{}"]'

lex_locators["modal"]["field_alert"] = "//div[contains(@class, 'forceFormPageError')]"

# I like the new markup I'm seeing in Spring '21!
lex_locators["object"]["field"] = "//lightning-input[.//label[text()='{}']]//input"
