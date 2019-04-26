from cumulusci.robotframework import locators_45

lex_locators = locators_45.lex_locators.copy()

# oof. This is gnarly.
# Apparently, in 45 all modal buttons are in a class named 'modal-footer'
# but in 46 some are in a class named 'actionsContainer' instead.
lex_locators["modal"]["button"] = "{}{}{}".format(
    "//div[contains(@class,'uiModal')]",
    "//div[contains(@class,'modal-footer') or contains(@class, 'actionsContainer')]",
    "//button[.//span[text()='{}']]",
)
