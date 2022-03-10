# Note: Unlike in traditional robot libraries, this docstring will end
# up in output from the libdoc task. For that to happen, it must be
# before the imports.

"""
The following page objects are automatically included when
importing the PageObject library. You should not directly import this
file.

"""

import re

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from SeleniumLibrary.errors import ElementNotFound

from cumulusci.robotframework.form_handlers import get_form_handler
from cumulusci.robotframework.pageobjects import BasePage, pageobject
from cumulusci.robotframework.utils import capture_screenshot_on_error

# This will appear in the generated documentation in place of
# the filename.
TITLE = "Base Page Objects"


@pageobject(page_type="Listing")
class ListingPage(BasePage):
    """Page object representing a Listing page

    When going to the Listing page, you need to specify the object name. You
    may also specify the name of a filter.

    Example

    | Go to page  Listing  Contact  filterName=Recent

    """

    def _go_to_page(self, filter_name=None, locator=None):
        url_template = "{root}/lightning/o/{object_name}/list"
        url = url_template.format(
            root=self.cumulusci.org.lightning_base_url, object_name=self.object_name
        )
        if filter_name:
            url += "?filterName={}".format(filter_name)
        self.selenium.go_to(url)
        self.salesforce.wait_until_loading_is_complete(locator=locator)

    def _is_current_page(self):
        self.selenium.location_should_contain(
            "/lightning/o/{}/list".format(self.object_name)
        )

    @capture_screenshot_on_error
    def select_rows(self, *items):
        """Check the checkbutton for one or more rows

        Arguments are one or more strings. Each row that contains one
        of the strings in any column will be clicked. Rows that have
        already been checked will remain checked.

        If no elements are found to match, this keyword will raise an error.

        Example

        The following example selects all rows that contain either
        John Doe or Jane Doe in any column.

        | Select Rows   John Doe  Jane Doe
        """
        for item in items:
            xpath = self.salesforce.get_locator("object_list.checkbutton", item)
            elements = self.selenium.get_webelements(xpath)
            if elements:
                for element in elements:
                    cb = element.find_element_by_tag_name("input")
                    if not cb.is_selected():
                        element.click()
            else:
                raise Exception(f"No rows matched '{item}'")

    @capture_screenshot_on_error
    def deselect_rows(self, *items):
        """Uncheck the checkbutton for one or more rows

         Arguments are one or more strings. Each row that contains one
         of the strings in any column will be delselected. Rows that are
         unchecked will remain unchecked.

         If no elements are found to match, this keyword will raise an error.

        Example

         The following example deselects all rows that contain either
         John Doe or Jane Doe in any column.

         | Select Rows   John Doe  Jane Doe

        """
        for item in items:
            xpath = self.salesforce.get_locator("object_list.checkbutton", item)
            elements = self.selenium.get_webelements(xpath)

            if elements:
                for element in elements:
                    cb = element.find_element_by_tag_name("input")
                    if cb.is_selected():
                        self.builtin.log(f"clicking on element for {item}")
                        element.click()
                    else:
                        self.builtin.log(f"NOT clicking on element for {item}")
            else:
                raise Exception(f"No rows matched '{item}'")


class ModalMixin:
    def _wait_to_appear(self, expected_heading=None):
        """Waits until the modal is visible"""
        locator = "//div[contains(@class, 'uiModal')]"
        if expected_heading:
            locator += f"//h2[text()='{expected_heading}']"
            error = f"A modal with the heading {expected_heading} did not appear before the timeout"
        else:
            error = "The modal did not appear before the timeout"

        self.salesforce.wait_for_aura()
        self.selenium.wait_until_element_is_visible(locator, error=error)

    @capture_screenshot_on_error
    def close_the_modal(self):
        """Closes the open modal"""

        locator = "css: button.slds-modal__close"
        self.selenium.wait_until_element_is_enabled(locator)
        self.selenium.click_element(locator)
        self.wait_until_modal_is_closed()
        self._remove_from_library_search_order()

    @capture_screenshot_on_error
    def click_modal_button(self, button_label):
        """Click the named modal button (Save, Save & New, Cancel, etc)"""
        # stolen from Salesforce.py:click_modal_button
        locator = f"sf:modal.button:{button_label}"
        self.selenium.wait_until_page_contains_element(locator)
        self.selenium.wait_until_element_is_enabled(locator)
        self.salesforce._jsclick(locator)

    @capture_screenshot_on_error
    def modal_should_contain_errors(self, *messages):
        """Verify that the modal contains the following errors

        This will look for the given message in the standard SLDS
        component (<ul class='errorsList'>)
        """
        for message in messages:
            locator = "//ul[@class='errorsList']//li[contains(., \"{}\")]".format(
                message
            )
            self.selenium.page_should_contain_element(
                locator,
                'The page did not contain an error with the text "{}"'.format(message),
            )

    @capture_screenshot_on_error
    def modal_should_show_edit_error_for_fields(self, *field_names):
        """Verify that a dialog is showing requiring a review of the given fields

        This works by looking for a the "we hit a snag" popup, and
        then looking for an anchor tag with the attribute
        force-recordediterror_recordediterror, along with the given
        text.

        """
        self.selenium.wait_until_page_contains_element("sf:modal.field_alert")
        for field_name in field_names:
            locator = f"sf:modal.review_alert:{field_name}"
            self.selenium.page_should_contain_element(
                locator, f"Unable to find alert with field '{field_name}'"
            )

    @capture_screenshot_on_error
    def populate_field(self, name, value):
        """Populate a field on the modal form

        Name must the the label of a field as it appears on the modal form.

        Example

        | Populate field  First Name  Connor
        | Populate field  Last Name   MacLeod
        """
        # For now, call the same keyword in Salesforce.py. Eventually
        # that keyword may get moved here and deprecated from that
        # library.
        self.salesforce.populate_field(name, value)

    @capture_screenshot_on_error
    def populate_form(self, *args, **kwargs):
        """Populate the modal form

        Arguments are of the form key=value, where 'key' represents
        a field name as it appears on the form (specifically, the text
        of a label with the class 'uiLabel').

        Example:

        | Populate form
        | ...  First Name=Connor
        | ...  Last Name=MacLeod
        """
        # For now, call the same keyword in Salesforce.py. Eventually
        # that keyword may get moved here and deprecated from that
        # library.
        self.salesforce.populate_form(*args, **kwargs)

    @capture_screenshot_on_error
    def select_dropdown_value(self, label, value):
        """Sets the value of a dropdown form field from one of the values in the dropdown

        ``label`` represents the label on the form field (eg: Lead Source)

        If a modal is present, the modal will be searched for the dropdown. Otherwise
        the first matching dropdown on the entire web page will be used.
        """
        locator = f"label:{label}"
        try:
            element = self.selenium.get_webelement(locator)
        except (NoSuchElementException, TimeoutException, ElementNotFound):
            raise ElementNotFound(f"Form element with label '{label}' was not found")

        self.salesforce.scroll_element_into_view(locator)
        handler = get_form_handler(element, locator)
        try:
            handler.set(value)
        except (NoSuchElementException, TimeoutException, ElementNotFound):
            raise ElementNotFound(f"Dropdown value '{value}' not found")

    @capture_screenshot_on_error
    def wait_until_modal_is_closed(self, timeout=None):
        """Waits until the modal is no longer visible

        If the modal isn't open, this will not throw an error.
        """
        locator = "//div[contains(@class, 'uiModal')]"

        self.selenium.wait_until_page_does_not_contain_element(locator)

    def _get_form_element_for_label(self, label):
        """Returns an element of class 'slds-form-element' which contains the given label.

        If you use this to find an item on a modal, you're responsible for waiting for the
        modal to appear before calling this function.
        """
        # search from the root of the document, unless a modal
        # is open
        root = self.selenium.driver.find_element_by_tag_name("body")
        with self._no_implicit_wait():
            # We don't want to wait, we just want to know if the
            # modal is alredy there or not. The caller should have
            # already waited for the modal.

            # also, we use find_elements (plural) here because it will
            # return an empty list rather than throwing an error
            modals = root.find_elements_by_xpath("//div[contains(@class, 'uiModal')]")
            # There should only ever be zero or one, but the Salesforce
            # UI never ceases to surprise me.
            modals = [m for m in modals if m.is_displayed()]
            if modals:
                root = modals[0]
        try:
            # As salesforce evolves, more and more fields use <label for='some-id'>
            # where "for" points to the associated input field. w00t! If we can,
            # use that. If not, fall back to an older strategy
            try:
                label_element = root.find_element_by_xpath(f'//label[text()="{label}"]')
                input_id = label_element.get_attribute("for")
                element = root.find_element_by_id(input_id)
                return element

            except NoSuchElementException:
                pass

            # gnarly, but effective.
            # this finds an element with the class slds-form-element which
            # has a child element with the class 'form-element__label' and
            # text that matches the given label.
            locator = f".//*[contains(@class, 'slds-form-element') and .//*[contains(@class, 'form-element__label')]/descendant-or-self::text()='{label}']"
            element = root.find_element_by_xpath(locator)
            return element

        except NoSuchElementException:
            raise ElementNotFound(f"Form element with label '{label}' was not found")


@pageobject("New")
class NewModal(ModalMixin, BasePage):
    """A page object representing the New Object modal

    Note: You should not use this page object with 'Go to page'. Instead,
    you can use 'Wait for modal to appear' after performing an action
    that causes the new object modal to appear (eg: clicking the
    "New" button). Once the modal appears, the keywords for that
    modal will be available for use in the test.

    Example:

    | Go to page                 Home  Contact
    | Click object button        New
    | Wait for modal to appear   New  Contact
    """


@pageobject("Edit")
class EditModal(ModalMixin, BasePage):
    """A page object representing the Edit Object modal

    Note: You should not use this page object with 'Go to page'. Instead,
    you can use 'Wait for modal to appear' after performing an action
    that causes the new object modal to appear (eg: clicking the
    "Edit" button). Once the modal appears, the keywords for that
    modal will be available for use in the test.

    Example:

    | Click object button        Edit
    | Wait for modal to appear   Edit  Contact

    """


@pageobject("Home")
class HomePage(BasePage):
    """A page object representing the home page of an object.

    When going to the Home page, you need to specify the object name.

    Note: The home page of an object may automatically redirect you to
    some other page, such as a Listing page. If you are working with
    such a page, you might need to use `page should be` to load the
    keywords for the page you expect to be redirected to.

    Example

    | Go to page  Home  Contact

    """

    def _go_to_page(self, locator=None):
        url_template = "{root}/lightning/o/{object_name}/home"
        url = url_template.format(
            root=self.cumulusci.org.lightning_base_url, object_name=self.object_name
        )
        self.selenium.go_to(url)
        self.salesforce.wait_until_loading_is_complete(locator=locator)

    def _is_current_page(self):
        self.selenium.location_should_contain(
            "/lightning/o/{}/home".format(self.object_name)
        )


@pageobject("Detail")
class DetailPage(BasePage):
    """A page object representing the standard Detail page.

    When going to this page via the standard `Go to page` keyword, you
    can specify either an object id, or a set of keyword arguments which
    will be used to look up the object id. When using keyword arguments,
    they need to represent a unique user.

    Example

    | ${contact_id} =       Salesforce Insert  Contact
    | ...                   FirstName=${first_name}
    | ...                   LastName=${last_name}
    |
    | # Using the id:
    | Go to page  Detail  Contact  ${contact_id}
    |
    | # Using lookup parameters
    | Go to page  Detail  Contact  FirstName=${first_name}  LastName=${last_name}

    """

    def _go_to_page(self, object_id=None, locator=None, **kwargs):
        """Go to the detail page for the given record.

        You may pass in an object id, or you may pass in keyword arguments
        which can be used to look up the object.

        Example

        | Go to page  Detail  Contact  firstName=John  lastName=Smith
        """

        if kwargs and object_id:
            raise Exception("Specify an object id or keyword arguments, but not both")

        if kwargs:
            # note: this will raise an exception if no object is found,
            # or if multiple objects are found.
            object_id = self._get_object(**kwargs)["Id"]

        url_template = "{root}/lightning/r/{object_name}/{object_id}/view"
        url = url_template.format(
            root=self.cumulusci.org.lightning_base_url,
            object_name=self.object_name,
            object_id=object_id,
        )
        self.selenium.go_to(url)
        self.salesforce.wait_until_loading_is_complete(locator=locator)

    def _is_current_page(self, **kwargs):
        """Verify we are on a detail page.

        If keyword arguments are present, this function will go a query
        on the given parameters, assert that the query returns a single
        result, and the verify that the returned object id is part of the url.
        """
        if kwargs:
            # do a lookup to get the object id
            object_id = self._get_object(**kwargs)["Id"]
            pattern = r"/lightning/r/{}/{}/view$".format(self.object_name, object_id)
        else:
            # no kwargs means we should just verify we are on a detail
            # page without regard to which object
            pattern = r"/lightning/r/{}/.*/view$".format(self.object_name)

        location = self.selenium.get_location()
        if not re.search(pattern, location):
            raise Exception(
                "Location '{}' didn't match pattern {}".format(location, pattern)
            )
