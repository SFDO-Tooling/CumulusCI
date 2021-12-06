import copy

from cumulusci.robotframework import locators_52

lex_locators = copy.deepcopy(locators_52.lex_locators)
lex_locators["object_list"] = {
    # Note: this matches the <td> with the checkbutton, not the inner checkbutton
    # This is because clicking the actual checkbutton will throw an error that
    # another element will receive the click.
    "checkbutton": '//tbody/tr[.//*[text()="{}"]]//td[.//input[@type="checkbox"]]',
    "status_info": "//force-list-view-manager-status-info",
}
