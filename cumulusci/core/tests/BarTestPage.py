"""
This class is used by test_pageobjects
"""
from cumulusci.robotframework.pageobjects import BasePage
from cumulusci.robotframework.pageobjects import pageobject


@pageobject(page_type="Test", object_name="Bar__c")
class BarTestPage(BasePage):
    def bar_keyword_1(self, message):
        self.builtin.log(message)
        return f"bar keyword 1: {message}"

    def bar_keyword_2(self, message):
        self.builtin.log(message)
        return f"bar keyword 2: {message}"
