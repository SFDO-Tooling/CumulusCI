from cumulusci.robotframework.pageobjects import BasePage
from cumulusci.robotframework.pageobjects import pageobject


@pageobject(page_type="Test", object_name="Foo__c")
class FooTestPage(BasePage):
    def foo_keyword_1(self, message):
        self.builtin.log(message)
        return "foo keyword 1: {}".format(message)
