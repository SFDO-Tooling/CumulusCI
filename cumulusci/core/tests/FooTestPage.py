from cumulusci.robotframework.pageobjects import BasePage
from cumulusci.robotframework.pageobjects import pageobject


@pageobject("Test", "Foo")
class FooTestPage(BasePage):
    object_name = "Foo"

    def foo_keyword_1(self, message):
        self.builtin.log(message)
        return "foo keyword 1: {}".format(message)
