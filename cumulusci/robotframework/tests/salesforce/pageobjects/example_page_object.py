from cumulusci.robotframework.pageobjects import BasePage
from cumulusci.robotframework.pageobjects import pageobject


@pageobject("About", "Blank")
class AboutBlankPage(BasePage):
    object_name = None

    def _go_to_page(self):
        self.selenium.go_to("about:blank")

    def _is_current_page(self):
        location = self.selenium.get_location()
        if location != "about:blank":
            raise Exception(
                "Expected location to be 'about:blank' but it was '{}'".format(location)
            )

    def hello(self, message):
        return "About:Blank Page says Hello, {}".format(message)

    def keyword_one(self):
        return "About:Blank keyword one"

    def keyword_two(self):
        return "About:Blank keyword two"
