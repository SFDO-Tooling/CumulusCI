from robot.libraries.BuiltIn import BuiltIn
from robot.api import logger
from selenium.webdriver.common.action_chains import ActionChains
from cumulusci.utils import get_all_subclasses

"""
FIXME: Something that still needs to be resolved is what to do about
name clashes. What if a project imports two different libraries and
each library implements a handler for the same tag and/or a handler
for which a built-in handler already exists. How do we decide what
takes precedence. Is this even something we have to worry about?

So, the idea is to find an element, then do something like
BaseFormHandler.get_handler(element, locator).set("foo")

"""


def get_form_handler(element, locator):
    """Return an instance of handler for the given element

    This will search all subclasses of BaseFormHandler, looking
    for a class that supports the tag_name of the given element
    """
    tag = element.tag_name
    for subclass in get_all_subclasses(BaseFormHandler):
        if tag in subclass.tags:
            # first one wins, but is that the right algorithm? Do
            # we want to give precedence to external handlers
            # over our built-in ones?
            return subclass(element, locator)
    return None


class BaseFormHandler:
    def __init__(self, element, locator):
        # concrete element to be handled
        self.element = element

        # the locator used to get the element, which we use for error
        # handling.
        self.locator = locator

    @property
    def selenium(self):
        return BuiltIn().get_library_instance("SeleniumLibrary")

    # these should be implemented by each of the handlers
    def set(self, value):
        pass

    def focus(self):
        pass

    def clear(self):
        pass


class InputHandler(BaseFormHandler):
    """An input handler for non-lightning input and textarea form fields

    This is the fallback handler for when we can't find a lightning component.
    """

    tags = ["input", "textarea"]

    def set(self, value):
        self.element.send_keys(value)

    def clear(self):
        """Remove the value in the element"""
        # oddly, element.clear() doesn't always work.
        self.selenium.driver.execute_script("arguments[0].value = '';", self.element)


class LightningComboboxHandler(BaseFormHandler):
    """An input handler for comboboxes"""

    tags = ["lightning-combobox"]

    def set(self, value):
        value_locator = f'//lightning-base-combobox-item[.="{value}"]'
        wait = 5
        try:
            self.element.click()
            self.selenium.wait_until_element_is_visible(value_locator, wait)
            self.selenium.click_element(value_locator)
        except Exception as e:
            logger.debug(f"exception: {e}")
            raise Exception(
                f"Dropdown value '{value}' for '{self.locator}' not found after {wait} seconds"
            )


class LightningInputHandler(BaseFormHandler):
    """An input handler for components that can be treated as an input or textarea"""

    tags = ["lightning-input", "lightning-textarea", "lightning-datepicker"]

    def set(self, value):
        self.focus()
        if self.element.get_attribute("type") == "checkbox":
            # lightning-input elements are used for checkboxes
            # as well as free text input.
            checked = self.element.get_attribute("checked")
            if (checked and value != "checked") or (not checked and value == "checked"):
                self.element.send_keys(" ")
        else:
            self.clear()
            self.element.send_keys(value)

    def clear(self):
        """Remove the value in the element"""
        # oddly, element.clear() doesn't always work.
        self.selenium.driver.execute_script("arguments[0].value = '';", self.element)

    def focus(self):
        """Set focus to the element

        In addition to merely setting the focus, we click on the
        element in case there are functions tied to that event.
        """
        actions = ActionChains(self.selenium.driver)
        actions.move_to_element(self.element).click().perform()
        self.selenium.set_focus_to_element(self.element)


class LightningLookupHandler(BaseFormHandler):
    tags = ["lightning-lookup", "lightning-grouped-combobox"]

    def set(self, value):
        wait = 5
        # I wonder if I should/could anchor this to the element
        # instead of searching the whole document?
        value_locator = f'//div[@role="listbox"]//*[.="{value}"]'
        self.element.click()
        self.element.send_keys(value)
        try:
            self.selenium.wait_until_element_is_visible(value_locator, wait)
            self.selenium.click_element(value_locator)
        except Exception as e:
            # *sigh* this still fails randomly even though
            # I can see the dadgum item in the dropdown.
            logger.debug(f"exception: {e}")
            raise Exception(
                f"Lookup value '{value}' for '{self.locator}' not found after {wait} seconds"
            )

    def clear(self):
        """Remove the value in the element"""
        # I'll get to this later...
        pass
