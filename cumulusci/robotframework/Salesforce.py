from robot.libraries.BuiltIn import BuiltIn
from cumulusci.robotframework.selectors import selectors

class Salesforce(object):
    def __init__(self):
        self.selenium = BuiltIn().get_library_instance('SeleniumLibrary')

    def open_app_launcher(self):
        self.selenium.click_button(selectors['app_launcher']['button'])

    def select_app_launcher_app(self, app_name):
        identifier = selectors['app_launcher']['app_link'].format(app_name)
        self.selenium.click_link(identifier)

    def select_app_launcher_tab(self, tab_name):
        identifier = selectors['app_launcher']['tab_link'].format(tab_name)
        self.selenium.click_link(identifier)
