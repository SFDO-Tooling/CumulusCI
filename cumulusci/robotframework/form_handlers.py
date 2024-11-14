import abc

from robot.libraries.BuiltIn import BuiltIn
from selenium.common.exceptions import TimeoutException

from cumulusci.utils.classutils import get_all_subclasses

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


class BaseFormHandler(abc.ABC):
    """Base class for all form handlers

    The goal is to have each handler implement the methods 'get',
    'set', 'focus', and 'clear'. However, at present we're only using
    'set' externally. 'focus' is the one method that will probably
    have the same implementation for every handler so it's defined in
    the base class. The others are abstract methods which each handler
    should define.

    """

    def __init__(self, element, locator):
        # concrete element to be handled
        self.element = element

        # the locator used to get the element, which we use for error
        # handling.
        self.locator = locator

    @property
    def selenium(self):
        return BuiltIn().get_library_instance("SeleniumLibrary")

    @property
    def input_element(self):
        """Returns the first <input> or <textarea> element inside the element"""
        elements = self.element.find_elements_by_xpath(
            ".//*[self::input or self::textarea]"
        )
        return elements[0] if elements else None

    @abc.abstractmethod
    def set(self, value):
        pass

    @abc.abstractmethod
    def get(self):
        pass

    @abc.abstractmethod
    def clear(self):
        pass

    def focus(self):
        """Set focus to the element

        In addition to merely setting the focus via selenium, we click
        on the element in case there are functions tied to that event.
        """
        self.selenium.set_focus_to_element(self.element)
        self.element.click()


class HTMLInputHandler(BaseFormHandler):
    """An input handler for non-lightning input and textarea form fields

    This is the fallback handler for when we can't find a lightning component.
    """

    tags = ["input", "textarea"]

    def set(self, value):
        if self.element.get_attribute("type") == "checkbox":
            value = value.lower()
            checked = self.element.is_selected()
            if (checked and value != "checked") or (not checked and value == "checked"):
                self.element.click()

        elif self.element.get_attribute("type") == "radio":
            if value.strip().lower() != "selected":
                raise Exception("value must be 'selected'")
            self.element.send_keys(" ")

        else:
            self.clear()
            self.element.send_keys(value)

    def get(self, value):
        # not currently being used
        pass  # pragma: no cover

    def clear(self):
        # Salesforce.py has a crazy amount of code for clearing
        # a field; for now these handlers seem to be working without it.
        self.selenium.driver.execute_script("arguments[0].value = '';", self.element)


class LightningComboboxHandler(BaseFormHandler):
    """An input handler for comboboxes"""

    tags = ["lightning-combobox"]

    @property
    def input_element(self):
        """Returns the base form element (input or button) that the combobox is based on"""
        elements = self.element.find_elements_by_xpath(
            ".//*[contains(@class, 'slds-combobox__input')]"
        )
        return elements[0] if elements else None

    def set(self, value):
        value_locator = f'//lightning-base-combobox-item[.="{value}"]'
        wait = 5
        try:
            # at this point, self.input_element is None
            self.input_element.click()
            self.selenium.wait_until_element_is_visible(value_locator, wait)
            self.selenium.click_element(value_locator)
        except Exception:
            raise TimeoutException(
                f"Dropdown value '{value}' for '{self.locator}' not found after {wait} seconds"
            )

    def get(self, value):
        # not currently being used
        pass  # pragma: no cover

    def clear(self):
        # not currently being used
        pass  # pragma: no cover


class LightningInputHandler(BaseFormHandler):
    """An input handler for components that can be treated as an input or textarea"""

    tags = [
        "lightning-primitive-input-checkbox",
        "lightning-primitive-input-simple",
        "lightning-textarea",
        "lightning-datepicker",
    ]

    def set(self, value):
        self.focus()
        if self.input_element.get_attribute("type") == "checkbox":
            # lightning-input elements are used for checkboxes
            # as well as free text input.
            checked = self.element.get_attribute("checked")
            if (checked and value != "checked") or (not checked and value == "checked"):
                self.input_element.send_keys(" ")

        elif self.input_element.get_attribute("type") == "radio":
            if value.strip().lower() != "selected":
                raise Exception("value must be 'selected'")
            self.input_element.send_keys(" ")

        else:
            self.clear()
            self.input_element.send_keys(value)

    def get(self, value):
        # not currently being used
        pass  # pragma: no cover

    def clear(self):
        # Salesforce.py has a crazy amount of code for clearing
        # a field; for now these handlers seem to be working without it.
        self.selenium.driver.execute_script("arguments[0].value = '';", self.element)


class LightningLookupHandler(BaseFormHandler):
    tags = ["lightning-lookup", "lightning-grouped-combobox"]

    def set(self, value):
        wait = 10
        # I wonder if I should/could anchor this to the element
        # instead of searching the whole document?
        value_locator = f'//lightning-base-combobox-formatted-text[@title="{value}"]'
        self.element.click()
        self.input_element.send_keys(value)
        try:
            self.selenium.wait_until_element_is_visible(value_locator, wait)
            self.selenium.click_element(value_locator)
        except Exception:
            raise TimeoutException(
                f"Lookup value '{value}' for '{self.locator}' not found after {wait} seconds"
            )

    def get(self, value):
        # not currently being used
        pass  # pragma: no cover

    def clear(self):
        # this is not currently being used
        pass  # pragma: no cover
