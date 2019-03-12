from robot.libraries.BuiltIn import BuiltIn
from cumulusci.robotframework import BaseLibrary
from cumulusci.robotframework.utils import selenium_retry
import time

"""
    execute javascript  raise_red()  # or maybe simulate_popup()
    execute javascript  setTimeout(function() {whatever}, 1000)
    # this should fail immediately, but pass after the retry
    click element with retry  id='red'
    ${duration}=  get duration of previous keyword

"""


class TestLibrary(BaseLibrary):
    def __init__(self):
        super(TestLibrary, self).__init__()
        self.duration = None
        self.initialized = True

    @property
    def builtin(self):
        return BuiltIn()

    def get_duration_of_previous_keyword(self):
        return self.duration

    def click_element_with_default_retry(self, locator):
        start = time.time()
        self.selenium.click_element(locator)
        end = time.time()
        self.duration = end - start

    @selenium_retry(True)
    def click_element_with_explicit_retry(self, locator):
        start = time.time()
        self.selenium.click_element(locator)
        end = time.time()
        self.duration = end - start

    @selenium_retry(False)
    def click_element_without_retry(self, locator):
        start = time.time()
        self.selenium.click_element(locator)
        end = time.time()
        self.duration = end - start
