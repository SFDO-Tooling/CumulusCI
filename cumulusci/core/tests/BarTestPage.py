"""
This class is used by test_pageobjects
"""
from cumulusci.robotframework.pageobjects import BasePage
from cumulusci.robotframework.pageobjects import pageobject


@pageobject("Test", "Bar")
class BarTestPage(BasePage):
    object_name = "Bar"

    def bar_keyword_1(self, message):
        self.builtin.log(message)
        return "bar keyword 1: {}".format(message)

    def bar_keyword_2(self, message):
        self.builtin.log(message)
        return "bar keyword 2: {}".format(message)
