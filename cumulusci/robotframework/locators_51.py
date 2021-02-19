from cumulusci.robotframework import locators_50
import copy

lex_locators = copy.deepcopy(locators_50.lex_locators)

lex_locators["modal"]["button"] = "//div[contains(@class,'uiModal')]//button[.='{}']"

lex_locators["modal"]["has_error"] = "css: div.forceFormPageError"

lex_locators["modal"][
    "review_alert"
] = '//a[@force-recordediterror_recordediterror and text()="{}"]'

lex_locators["modal"]["field_alert"] = "//div[contains(@class, 'forceFormPageError')]"

# I like the new markup I'm seeing in Spring '21!
lex_locators["object"]["field"] = "//lightning-input[.//label[text()='{}']]//input"

lex_locators["record"]["related"]["button"] = (
    # the old locator searched for an <a> element, but in spring '21
    # the buttons are sometimes <button> elements. To be liberal in what
    # we accept, we'll just find anything that has the exact text.
    "//*[@data-component-id='force_relatedListContainer']"
    "//article[contains(@class, 'slds-card slds-card_boundary')]"
    "[.//span[@title='{}']]//*[text()='{}']"
)
