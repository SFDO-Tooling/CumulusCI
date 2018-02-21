from robot.libraries.BuiltIn import BuiltIn
from cumulusci.robotframework.selectors import selectors

class Salesforce(object):
    def __init__(self):
        self.selenium = BuiltIn().get_library_instance('SeleniumLibrary')
        self.cumulusci = BuiltIn().get_library_instance('cumulusci.robotframework.CumulusCI')

    def current_app_should_be(self, app_name):
        locator = selectors['app_launcher']['current_app'].format(app_name)
        elem = self.selenium.get_webelement(locator)
        return elem.text

    def open_app_launcher(self):
        self.selenium.set_focus_to_element(selectors['app_launcher']['button'])
        self.selenium.click_button(selectors['app_launcher']['button'])

    def select_app_launcher_app(self, app_name):
        locator = selectors['app_launcher']['app_link'].format(app_name)
        self.selenium.wait_until_page_contains_element(locator)
        elem = self.selenium.get_webelement(locator)
        link = elem.find_element_by_xpath('../../..')
        link.click()

    def select_app_launcher_tab(self, tab_name):
        locator = selectors['app_launcher']['tab_link'].format(tab_name)
        self.selenium.click_link(locator)

    def soql_query(self, query):
        return self.cumulusci.sf.query(query)
