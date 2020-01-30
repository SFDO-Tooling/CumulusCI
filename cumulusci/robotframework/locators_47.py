from cumulusci.robotframework import locators_46

lex_locators = locators_46.lex_locators.copy()

lex_locators["record"]["related"][
    "link"
] = "//article[.//span[@title='{}']]//a[.//span[@title='{}']]"
lex_locators["record"]["related"][
    "popup_trigger"
] = "//article[.//span[@title='{}'][//a[text()='{}']]]//div[contains(@class, 'forceVirtualAction')]/a"
lex_locators["object"][
    "field_label"
] = "//label[@for!='' and text()='{}']|//label[@for!=''][./span[text()='{}']]"
