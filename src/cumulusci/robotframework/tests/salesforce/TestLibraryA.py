"""
This is a library used by locators.robot for testing
custom locator strategies
"""
from cumulusci.robotframework.locator_manager import (
    register_locators,
    translate_locator,
)

locators = {
    # eg: A:breadcrumb:Home
    "breadcrumb": "//span[contains(@class, 'breadcrumbDetail') and text()='{}']",
    "something": "//whatever",
}


class TestLibraryA:
    ROBOT_LIBRARY_SCOPE = "global"

    def __init__(self):
        register_locators("A", locators)

    def translate_locator(self, prefix, locator):
        return translate_locator(prefix, locator)
