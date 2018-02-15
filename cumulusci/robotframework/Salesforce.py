from robot.libraries.BuiltIn import BuiltIn
from cumulusci.robotframework import salesforce_identifiers as identifiers

class Salesforce(object):
    def __init__(self):
        self.selenium = BuiltIn().get_library_instance('SeleniumLibrary')

    def open_app_launcher(self):
        self.selenium.click_button(identifiers.app_launcher_button)

    def select_app_launcher_app(self, app_name):
        identifier = identifiers.app_launcher_app_link.format(app_name)
        self.selenium.click_link(identifier)
