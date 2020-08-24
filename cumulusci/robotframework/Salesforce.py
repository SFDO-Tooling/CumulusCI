import importlib
import logging
import re
import time

from pprint import pformat
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from robot.utils import timestr_to_secs
from cumulusci.robotframework.utils import get_locator_module_name
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
)
import faker

from simple_salesforce import SalesforceResourceNotFound
from cumulusci.robotframework.utils import selenium_retry, capture_screenshot_on_error
from SeleniumLibrary.errors import ElementNotFound, NoOpenBrowser
from urllib3.exceptions import ProtocolError

from cumulusci.core.template_utils import format_str
from cumulusci.robotframework import locator_manager

OID_REGEX = r"^(%2F)?([a-zA-Z0-9]{15,18})$"
STATUS_KEY = ("status",)

lex_locators = {}  # will be initialized when Salesforce is instantiated

# https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_composite_sobjects_collections_create.htm
SF_COLLECTION_INSERTION_LIMIT = 200


@selenium_retry
class Salesforce(object):
    """A keyword library for working with Salesforce Lightning pages

    While you can import this directly into any suite, the recommended way
    to include this in a test suite is to import the ``Salesforce.robot``
    resource file.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, debug=False, locators=None):
        self.debug = debug
        self._session_records = []
        # Turn off info logging of all http requests
        logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(
            logging.WARN
        )
        if locators:
            lex_locators.update(locators)
        else:
            self._init_locators()

        self._faker = faker.Faker("en_US")
        try:
            self.builtin.set_global_variable("${faker}", self._faker)
        except RobotNotRunningError:
            # this only happens during unit tests, and we don't care.
            pass

    def _init_locators(self):
        """Load the appropriate locator file for the current version

        If no version can be determined, we'll use the highest numbered
        locator file name.
        """
        try:
            version = int(float(self.get_latest_api_version()))
            self.builtin.set_suite_metadata("Salesforce API Version", version)
        except RobotNotRunningError:
            # Likely this means we are running in the context of
            # documentation generation. Setting the version to
            # None will result in using the latest version of
            # locators.
            version = None

        locator_module_name = get_locator_module_name(version)
        self.locators_module = importlib.import_module(locator_module_name)
        lex_locators.update(self.locators_module.lex_locators)

    @property
    def builtin(self):
        return BuiltIn()

    @property
    def cumulusci(self):
        return self.builtin.get_library_instance("cumulusci.robotframework.CumulusCI")

    def initialize_location_strategies(self):
        """Initialize the Salesforce location strategies 'text' and 'title'
        plus any strategies registered by other keyword libraries

        Note: This keyword is called automatically from *Open Test Browser*
        """
        locator_manager.register_locators("sf", lex_locators)
        locator_manager.register_locators("text", "Salesforce.Locate Element by Text")
        locator_manager.register_locators("title", "Salesforce.Locate Element by Title")

        # This does the work of actually adding all of the above-registered
        # location strategies, plus any that were registered by keyword
        # libraries.
        locator_manager.add_location_strategies()

    @selenium_retry(False)
    def _jsclick(self, locator):
        """Use javascript to click an element on the page

        See https://help.salesforce.com/articleView?id=000352057&language=en_US&mode=1&type=1
        """

        self.selenium.wait_until_page_contains_element(locator)
        self.selenium.wait_until_element_is_enabled(locator)
        for should_retry in (True, False):
            try:
                # Setting the focus first seems to be required as of Spring'20
                # (read: without it, tests started failing in that release). I
                # suspect it's because there is a focusOut handler on form
                # fields which need to be triggered for data to be accepted.
                element = self.selenium.get_webelement(locator)
                self.selenium.driver.execute_script(
                    "arguments[0].focus(); arguments[0].click()", element
                )
                return
            except StaleElementReferenceException:
                if should_retry:
                    time.sleep(1)
                else:
                    raise

    def set_faker_locale(self, locale):
        """Set the locale for fake data

        This sets the locale for all calls to the ``Faker`` keyword
        and ``${faker}`` variable. The default is en_US

        For a list of supported locales see
        [https://faker.readthedocs.io/en/master/locales.html|Localized Providers]
        in the Faker documentation.

        Example

        | Set Faker Locale    fr_FR
        | ${french_address}=  Faker  address

        """
        try:
            self._faker = faker.Faker(locale)
        except AttributeError:
            raise Exception(f"Unknown locale for fake data: '{locale}'")

    def get_fake_data(self, fake, *args, **kwargs):
        """Return fake data

        This uses the [https://faker.readthedocs.io/en/master/|Faker]
        library to provide fake data in a variety of formats (names,
        addresses, credit card numbers, dates, phone numbers, etc) and
        locales (en_US, fr_FR, etc).

        The _fake_ argument is the name of a faker property such as
        ``first_name``, ``address``, ``lorem``, etc. Additional
        arguments depend on type of data requested. For a
        comprehensive list of the types of fake data that can be
        generated see
        [https://faker.readthedocs.io/en/master/providers.html|Faker
        providers] in the Faker documentation.

        The return value is typically a string, though in some cases
        some other type of object will be returned. For example, the
        ``date_between`` fake returns a
        [https://docs.python.org/3/library/datetime.html#date-objects|datetime.date
        object]. Each time a piece of fake data is requested it will
        be regenerated, so that multiple calls will usually return
        different data.

        This keyword can also be called using robot's extended variable
        syntax using the variable ``${faker}``. In such a case, the
        data being asked for is a method call and arguments must be
        enclosed in parentheses and be quoted. Arguments should not be
        quoted when using the keyword.

        To generate fake data for a locale other than en_US, use
        the keyword ``Set Faker Locale`` prior to calling this keyword.

        Examples

        | # Generate a fake first name
        | ${first_name}=  Get fake data  first_name

        | # Generate a fake date in the default format
        | ${date}=  Get fake data  date

        | # Generate a fake date with an explicit format
        | ${date}=  Get fake data  date  pattern=%Y-%m-%d

        | # Generate a fake date using extended variable syntax
        | Input text  //input  ${faker.date(pattern='%Y-%m-%d')}

        """
        try:
            return self._faker.format(fake, *args, **kwargs)
        except AttributeError:
            raise Exception(f"Unknown fake data request: '{fake}'")

    def get_latest_api_version(self):
        return self.cumulusci.org.latest_api_version

    def create_webdriver_with_retry(self, *args, **kwargs):
        """Call the Create Webdriver keyword.

        Retry on connection resets which can happen if custom domain propagation is slow.
        """
        # Get selenium without referencing selenium.driver which doesn't exist yet
        selenium = self.builtin.get_library_instance("SeleniumLibrary")
        for _ in range(12):
            try:
                return selenium.create_webdriver(*args, **kwargs)
            except ProtocolError:
                # Give browser some more time to start up
                time.sleep(5)
        raise Exception("Could not connect to remote webdriver after 1 minute")

    @capture_screenshot_on_error
    def click_modal_button(self, title):
        """Clicks a button in a Lightning modal."""
        locator = lex_locators["modal"]["button"].format(title)
        self.selenium.wait_until_page_contains_element(locator)
        self.selenium.wait_until_element_is_enabled(locator)
        self._jsclick(locator)

    @capture_screenshot_on_error
    def click_object_button(self, title):
        """Clicks a button in an object's actions."""
        locator = lex_locators["object"]["button"].format(title=title)
        self._jsclick(locator)
        self.wait_until_modal_is_open()

    def load_related_list(self, heading):
        """Scrolls down until the specified related list loads.
        """
        locator = lex_locators["record"]["related"]["card"].format(heading)
        el = None
        i = 0
        while el is None:
            i += 1
            if i > 50:
                raise AssertionError(
                    "Timed out waiting for {} related list to load.".format(heading)
                )
            self.selenium.execute_javascript("window.scrollBy(0, 100)")
            self.wait_for_aura()
            try:
                self.selenium.get_webelement(locator)
                break
            except ElementNotFound:
                time.sleep(0.2)
                continue

    def click_related_list_button(self, heading, button_title):
        """Clicks a button in the heading of a related list.

        Waits for a modal to open after clicking the button.
        """
        self.load_related_list(heading)
        locator = lex_locators["record"]["related"]["button"].format(
            heading, button_title
        )
        self._jsclick(locator)
        self.wait_until_modal_is_open()

    @capture_screenshot_on_error
    def click_related_item_link(self, heading, title):
        """Clicks a link in the related list with the specified heading.

         This keyword will automatically call *Wait until loading is complete*.
        """
        self.load_related_list(heading)
        locator = lex_locators["record"]["related"]["link"].format(heading, title)
        try:
            self._jsclick(locator)
        except Exception as e:
            self.builtin.log(f"Exception: {e}", "DEBUG")
            raise Exception(
                f"Unable to find related link under heading '{heading}' with the text '{title}'"
            )
        self.wait_until_loading_is_complete()

    def click_related_item_popup_link(self, heading, title, link):
        """Clicks a link in the popup menu for a related list item.

        heading specifies the name of the list,
        title specifies the name of the item,
        and link specifies the name of the link
        """
        self.load_related_list(heading)
        locator = lex_locators["record"]["related"]["popup_trigger"].format(
            heading, title
        )

        self.selenium.wait_until_page_contains_element(locator)
        self._jsclick(locator)
        locator = lex_locators["popup"]["link"].format(link)
        self._jsclick(locator)
        self.wait_until_loading_is_complete()

    def close_modal(self):
        """ Closes the open modal """
        locator = lex_locators["modal"]["close"]
        self._jsclick(locator)

    def current_app_should_be(self, app_name):
        """ Validates the currently selected Salesforce App """
        locator = lex_locators["app_launcher"]["current_app"].format(app_name)
        elem = self.selenium.get_webelement(locator)
        assert app_name == elem.text, "Expected app to be {} but found {}".format(
            app_name, elem.text
        )

    def delete_session_records(self):
        """Deletes records that were created while running this test case.

        (Only records specifically recorded using the Store Session Record
        keyword are deleted.)
        """
        self._session_records.reverse()
        self.builtin.log("Deleting {} records".format(len(self._session_records)))
        for record in self._session_records[:]:
            self.builtin.log("  Deleting {type} {id}".format(**record))
            try:
                self.salesforce_delete(record["type"], record["id"])
            except SalesforceResourceNotFound:
                self.builtin.log("    {type} {id} is already deleted".format(**record))
            except Exception as e:
                self.builtin.log(
                    "    {type} {id} could not be deleted:".format(**record),
                    level="WARN",
                )
                self.builtin.log("      {}".format(e), level="WARN")

    def get_active_browser_ids(self):
        """Return the id of all open browser ids"""

        # This relies on some private data structures, but presently
        # there is no other way. There's been a discussion in the
        # robot slack channels about adding a new keyword that does
        # what this keyword does. When that happens, we can remove
        # this keyword.
        driver_ids = []
        try:
            driver_cache = self.selenium._drivers
        except NoOpenBrowser:
            return []

        for index, driver in enumerate(driver_cache._connections):
            if driver not in driver_cache._closed:
                # SeleniumLibrary driver ids start at one rather than zero
                driver_ids.append(index + 1)
        return driver_ids

    def get_current_record_id(self):
        """ Parses the current url to get the object id of the current record.
            Expects url format like: [a-zA-Z0-9]{15,18}
        """
        url = self.selenium.get_location()
        for part in url.split("/"):
            oid_match = re.match(OID_REGEX, part)
            if oid_match is not None:
                return oid_match.group(2)
        raise AssertionError("Could not parse record id from url: {}".format(url))

    def get_field_value(self, label):
        """Return the current value of a form field based on the field label"""
        input_element_id = self.selenium.get_element_attribute(
            "xpath://label[contains(., '{}')]".format(label), "for"
        )
        value = self.selenium.get_value(input_element_id)
        return value

    def get_locator(self, path, *args, **kwargs):
        """ Returns a rendered locator string from the Salesforce lex_locators
            dictionary.  This can be useful if you want to use an element in
            a different way than the built in keywords allow.
        """
        locator = lex_locators
        for key in path.split("."):
            locator = locator[key]
        return locator.format(*args, **kwargs)

    def get_record_type_id(self, obj_type, developer_name):
        """Returns the Record Type Id for a record type name"""
        soql = "SELECT Id FROM RecordType WHERE SObjectType='{}' and DeveloperName='{}'".format(
            obj_type, developer_name
        )
        res = self.cumulusci.sf.query_all(soql)
        return res["records"][0]["Id"]

    def get_related_list_count(self, heading):
        """Returns the number of items indicated for a related list."""
        locator = lex_locators["record"]["related"]["count"].format(heading)
        count = self.selenium.get_webelement(locator).text
        count = count.replace("(", "").replace(")", "")
        return int(count)

    def go_to_object_home(self, obj_name):
        """ Navigates to the Home view of a Salesforce Object """
        url = self.cumulusci.org.lightning_base_url
        url = "{}/lightning/o/{}/home".format(url, obj_name)
        self.selenium.go_to(url)
        self.wait_until_loading_is_complete(lex_locators["actions"])

    def go_to_object_list(self, obj_name, filter_name=None):
        """ Navigates to the Home view of a Salesforce Object """
        url = self.cumulusci.org.lightning_base_url
        url = "{}/lightning/o/{}/list".format(url, obj_name)
        if filter_name:
            url += "?filterName={}".format(filter_name)
        self.selenium.go_to(url)
        self.wait_until_loading_is_complete(lex_locators["actions"])

    def go_to_record_home(self, obj_id):
        """ Navigates to the Home view of a Salesforce Object """
        url = self.cumulusci.org.lightning_base_url
        url = "{}/lightning/r/{}/view".format(url, obj_id)
        self.selenium.go_to(url)
        self.wait_until_loading_is_complete(lex_locators["actions"])

    def go_to_setup_home(self):
        """ Navigates to the Home tab of Salesforce Setup """
        url = self.cumulusci.org.lightning_base_url
        self.selenium.go_to(url + "/lightning/setup/SetupOneHome/home")
        self.wait_until_loading_is_complete()

    def go_to_setup_object_manager(self):
        """ Navigates to the Object Manager tab of Salesforce Setup """
        url = self.cumulusci.org.lightning_base_url
        self.selenium.go_to(url + "/lightning/setup/ObjectManager/home")
        self.wait_until_loading_is_complete()

    def header_field_should_have_value(self, label):
        """ Validates that a field in the record header has a text value.
            NOTE: Use other keywords for non-string value types
        """
        locator = lex_locators["record"]["header"]["field_value"].format(label)
        self.selenium.page_should_contain_element(locator)

    def header_field_should_not_have_value(self, label):
        """ Validates that a field in the record header does not have a value.
            NOTE: Use other keywords for non-string value types
        """
        locator = lex_locators["record"]["header"]["field_value"].format(label)
        self.selenium.page_should_not_contain_element(locator)

    def header_field_should_have_link(self, label):
        """ Validates that a field in the record header has a link as its value """
        locator = lex_locators["record"]["header"]["field_value_link"].format(label)
        self.selenium.page_should_contain_element(locator)

    def header_field_should_not_have_link(self, label):
        """ Validates that a field in the record header does not have a link as its value """
        locator = lex_locators["record"]["header"]["field_value_link"].format(label)
        self.selenium.page_should_not_contain_element(locator)

    def click_header_field_link(self, label):
        """Clicks a link in record header."""
        locator = lex_locators["record"]["header"]["field_value_link"].format(label)
        self._jsclick(locator)

    def header_field_should_be_checked(self, label):
        """ Validates that a checkbox field in the record header is checked """
        locator = lex_locators["record"]["header"]["field_value_checked"].format(label)
        self.selenium.page_should_contain_element(locator)

    def header_field_should_be_unchecked(self, label):
        """ Validates that a checkbox field in the record header is unchecked """
        locator = lex_locators["record"]["header"]["field_value_unchecked"].format(
            label
        )
        self.selenium.page_should_contain_element(locator)

    def log_browser_capabilities(self, loglevel="INFO"):
        """Logs all of the browser capabilities as reported by selenium"""
        output = "selenium browser capabilities:\n"
        output += pformat(self.selenium.driver.capabilities, indent=4)
        self.builtin.log(output, level=loglevel)

    @capture_screenshot_on_error
    def open_app_launcher(self, retry=True):
        """Opens the Saleforce App Launcher Modal

        Note: starting with Spring '20 the app launcher button opens a
        menu rather than a modal. To maintain backwards compatibility,
        this keyword will continue to open the modal rather than the
        menu. If you need to interact with the app launcher menu, you
        will need to create a custom keyword.

        If the retry parameter is true, the keyword will
        close and then re-open the app launcher if it times out
        while waiting for the dialog to open.
        """

        self._jsclick("sf:app_launcher.button")
        self._jsclick("sf:app_launcher.view_all")
        self.wait_until_modal_is_open()
        try:
            # the modal may be open, but not yet fully rendered
            # wait until at least one link appears. We've seen that sometimes
            # the dialog hangs prior to any links showing up
            self.selenium.wait_until_element_is_visible(
                "xpath://ul[contains(@class, 'al-modal-list')]//li"
            )

        except Exception as e:
            # This should never happen, yet it does. Experience has
            # shown that sometimes (at least in spring '20) the modal
            # never renders. Refreshing the modal seems to fix it.
            if retry:
                self.builtin.log(
                    f"caught exception {e} waiting for app launcher; retrying", "DEBUG"
                )
                self.selenium.press_keys("sf:modal.is_open", "ESCAPE")
                self.wait_until_modal_is_closed()
                self.open_app_launcher(retry=False)
            else:
                self.builtin.log(
                    "caught exception waiting for app launcher; not retrying", "DEBUG"
                )
                raise

    def populate_field(self, name, value):
        """Enters a value into an input or textarea field.

        'name' represents the label on the page (eg: "First Name"),
        and 'value' is the new value.

        Any existing value will be replaced.
        """
        locator = self._get_input_field_locator(name)
        self._populate_field(locator, value)

    def populate_lookup_field(self, name, value):
        """Enters a value into a lookup field.
        """
        input_locator = self._get_input_field_locator(name)
        menu_locator = lex_locators["object"]["field_lookup_link"].format(value)

        self._populate_field(input_locator, value)

        for x in range(3):
            self.wait_for_aura()
            try:
                self.selenium.get_webelement(menu_locator)
            except ElementNotFound:
                # Give indexing a chance to catch up
                time.sleep(2)
                field = self.selenium.get_webelement(input_locator)
                field.send_keys(Keys.BACK_SPACE)
            else:
                break
        self.selenium.set_focus_to_element(menu_locator)
        self._jsclick(menu_locator)

    def _get_input_field_locator(self, name):
        """Given an input field label, return a locator for the related input field

        This looks for a <label> element with the given text, or
        a label with a span with the given text. The value of the
        'for' attribute is then extracted from the label and used
        to create a new locator with that id.

        For example, the locator 'abc123' will be returned
        for the following html:

        <label for='abc123'>First Name</label>
        -or-
        <label for='abc123'><span>First Name</span>
        """
        try:
            # we need to make sure that if a modal is open, we only find
            # the input element inside the modal. Otherwise it's possible
            # that the xpath could pick the wrong element.
            self.selenium.get_webelement(lex_locators["modal"]["is_open"])
            modal_prefix = "//div[contains(@class, 'modal-container')]"
        except ElementNotFound:
            modal_prefix = ""

        locator = modal_prefix + lex_locators["object"]["field_label"].format(
            name, name
        )
        input_element_id = self.selenium.get_element_attribute(locator, "for")
        return input_element_id

    def _populate_field(self, locator, value):
        self.builtin.log(f"value: {value}' locator: '{locator}'", "DEBUG")
        field = self.selenium.get_webelement(locator)
        self._focus(field)
        if field.get_attribute("value"):
            self._clear(field)
        actions = ActionChains(self.selenium.driver)
        actions.send_keys_to_element(field, value).perform()

    def _focus(self, element):
        """Set focus to an element

        In addition to merely setting the focus, we click the mouse
        to the field in case there are functions tied to that event.
        """
        actions = ActionChains(self.selenium.driver)
        actions.move_to_element(element).click().perform()
        self.selenium.set_focus_to_element(element)

    def _clear(self, element):
        """Clear the field, using any means necessary

        This is surprisingly hard to do with a generic solution. Some
        methods work for some components and/or on some browsers but
        not others. Therefore, several techniques are employed.
        """

        element.clear()
        self.selenium.driver.execute_script("arguments[0].value = '';", element)

        # Select all and delete just in case the element didn't get cleared
        element.send_keys(Keys.HOME + Keys.SHIFT + Keys.END)
        element.send_keys(Keys.BACKSPACE)

        if element.get_attribute("value"):
            # Give the UI a chance to settle down. The sleep appears
            # necessary. Without it, this keyword sometimes fails to work
            # properly. With it, I was able to run 700+ tests without a single
            # failure.
            time.sleep(0.25)

        # Even after all that, some elements refuse to be cleared out.
        # I'm looking at you, currency fields on Firefox.
        if element.get_attribute("value"):
            self._force_clear(element)

    def _force_clear(self, element):
        """Use brute-force to clear an element

        This moves the cursor to the end of the input field and
        then issues a series of backspace keys to delete the data
        in the field.
        """
        value = element.get_attribute("value")
        actions = ActionChains(self.selenium.driver)
        actions.move_to_element(element).click().send_keys(Keys.END)
        for character in value:
            actions.send_keys(Keys.BACKSPACE)
        actions.perform()

    def populate_form(self, **kwargs):
        """Enters multiple values from a mapping into form fields."""
        for name, value in kwargs.items():
            self.populate_field(name, value)

    def remove_session_record(self, obj_type, obj_id):
        """Remove a record from the list of records that should be automatically removed."""
        try:
            self._session_records.remove({"type": obj_type, "id": obj_id})
        except ValueError:
            self.builtin.log(
                "Did not find record {} {} in the session records list".format(
                    obj_type, obj_id
                )
            )

    def select_record_type(self, label):
        """Selects a record type while adding an object."""
        self.wait_until_modal_is_open()
        locator = lex_locators["object"]["record_type_option"].format(label)
        self._jsclick(locator)
        self.selenium.click_button("Next")

    @capture_screenshot_on_error
    def select_app_launcher_app(self, app_name):
        """Navigates to a Salesforce App via the App Launcher """
        locator = lex_locators["app_launcher"]["app_link"].format(app_name)
        self.open_app_launcher()
        self.selenium.wait_until_page_contains_element(locator, timeout=30)
        self.selenium.set_focus_to_element(locator)
        elem = self.selenium.get_webelement(locator)
        link = elem.find_element_by_xpath("../../..")
        self.selenium.set_focus_to_element(link)
        link.click()
        self.wait_until_modal_is_closed()

    @capture_screenshot_on_error
    def select_app_launcher_tab(self, tab_name):
        """Navigates to a tab via the App Launcher"""
        locator = lex_locators["app_launcher"]["tab_link"].format(tab_name)
        self.open_app_launcher()
        self.selenium.wait_until_page_contains_element(locator)
        self.selenium.set_focus_to_element(locator)
        self._jsclick(locator)
        self.wait_until_modal_is_closed()

    def salesforce_delete(self, obj_name, obj_id):
        """Deletes a Salesforce object by object name and Id.

        Example:

        The following example assumes that ``${contact id}`` has been
        previously set. The example deletes the Contact with that Id.

        | Salesforce Delete  Contact  ${contact id}
        """
        self.builtin.log("Deleting {} with Id {}".format(obj_name, obj_id))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        obj_class.delete(obj_id)
        self.remove_session_record(obj_name, obj_id)

    def salesforce_get(self, obj_name, obj_id):
        """Gets a Salesforce object by Id and returns the result as a dict.

        Example:

        The following example assumes that ``${contact id}`` has been
        previously set. The example retrieves the Contact object with
        that Id and then logs the Name field.

        | &{contact}=  Salesforce Get  Contact  ${contact id}
        | log  Contact name:  ${contact['Name']}

        """
        self.builtin.log(f"Getting {obj_name} with Id {obj_id}")
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.get(obj_id)

    def salesforce_insert(self, obj_name, **kwargs):
        """Creates a new Salesforce object and returns the Id.

        The fields of the object may be defined with keyword arguments
        where the keyword name is the same as the field name.

        The object name and Id is passed to the *Store Session
        Record* keyword, and will be deleted when the keyword
        *Delete Session Records* is called.

        As a best practice, either *Delete Session Records* or
        *Delete Records and Close Browser* from Salesforce.robot
        should be called as a suite teardown.

        Example:

        The following example creates a new Contact with the
        first name of "Eleanor" and the last name of "Rigby".

        | ${contact id}=  Salesforce Insert  Contact
        | ...  FirstName=Eleanor
        | ...  LastName=Rigby

        """
        self.builtin.log("Inserting {} with values {}".format(obj_name, kwargs))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        res = obj_class.create(kwargs)
        self.store_session_record(obj_name, res["id"])
        return res["id"]

    def _salesforce_generate_object(self, obj_name, **fields):
        obj = {"attributes": {"type": obj_name}}  # Object type to create
        obj.update(fields)
        return obj

    def generate_test_data(self, obj_name, number_to_create, **fields):
        """Generate bulk test data

        This returns an array of dictionaries with template-formatted
        arguments which can be passed to the *Salesforce Collection Insert*
        keyword.

        You can use ``{{number}}`` to represent the unique index of
        the row in the list of rows.  If the entire string consists of
        a number, Salesforce API will treat the value as a number.

        Example:

        The following example creates three new Contacts:

            | @{objects} =  Generate Test Data  Contact  3
            | ...  Name=User {{number}}
            | ...  Age={{number}}

        The example code will generate Contact objects with these fields:

            | [{'Name': 'User 0', 'Age': '0'},
            |  {'Name': 'User 1', 'Age': '1'},
            |  {'Name': 'User 2', 'Age': '2'}]

        Python Expression Syntax is allowed so computed templates like this are also allowed: ``{{1000 + number}}``

        Python operators can be used, but no functions or variables are provided, so mostly you just
        have access to mathematical and logical operators. The Python operators are described here:

        https://www.digitalocean.com/community/tutorials/how-to-do-math-in-python-3-with-operators

        Contact the CCI team if you have a use-case that
        could benefit from more expression language power.

        Templates can also be based on faker patterns like those described here:

        https://faker.readthedocs.io/en/master/providers.html

        Most examples can be pasted into templates verbatim:

            | @{objects}=  Generate Test Data  Contact  200
            | ...  Name={{fake.first_name}} {{fake.last_name}}
            | ...  MailingStreet={{fake.street_address}}
            | ...  MailingCity=New York
            | ...  MailingState=NY
            | ...  MailingPostalCode=12345
            | ...  Email={{fake.email(domain="salesforce.com")}}

        """
        objs = []

        for i in range(int(number_to_create)):
            formatted_fields = {
                name: format_str(value, {"number": i}) for name, value in fields.items()
            }
            newobj = self._salesforce_generate_object(obj_name, **formatted_fields)
            objs.append(newobj)

        return objs

    def salesforce_collection_insert(self, objects):
        """Inserts records that were created with *Generate Test Data*.

        _objects_ is a list of data, typically generated by the
        *Generate Test Data* keyword.

        A 200 record limit is enforced by the Salesforce APIs.

        The object name and Id is passed to the *Store Session
        Record* keyword, and will be deleted when the keyword *Delete
        Session Records* is called.

        As a best practice, either *Delete Session Records* or
        **Delete Records and Close Browser* from Salesforce.robot
        should be called as a suite teardown.

        Example:

        | @{objects}=  Generate Test Data  Contact  200
        | ...  FirstName=User {{number}}
        | ...  LastName={{fake.last_name}}
        | Salesforce Collection Insert  ${objects}

        """
        assert (
            not obj.get("id", None) for obj in objects
        ), "Insertable objects should not have IDs"
        assert len(objects) <= SF_COLLECTION_INSERTION_LIMIT, (
            "Cannot insert more than %s objects with this keyword"
            % SF_COLLECTION_INSERTION_LIMIT
        )

        records = self.cumulusci.sf.restful(
            "composite/sobjects",
            method="POST",
            json={"allOrNone": True, "records": objects},
        )

        for idx, (record, obj) in enumerate(zip(records, objects)):
            if record["errors"]:
                raise AssertionError(
                    "Error on Object {idx}: {record} : {obj}".format(**vars())
                )
            self.store_session_record(obj["attributes"]["type"], record["id"])
            obj["id"] = record["id"]
            obj[STATUS_KEY] = record

        return objects

    def salesforce_collection_update(self, objects):
        """Updates records described as Robot/Python dictionaries.

        _objects_ is a dictionary of data in the format returned
        by the *Salesforce Collection Insert* keyword.

        A 200 record limit is enforced by the Salesforce APIs.

        Example:

        The following example creates ten accounts and then updates
        the Rating from "Cold" to "Hot"

        | ${data}=  Generate Test Data  Account  10
        | ...  Name=Account #{{number}}
        | ...  Rating=Cold
        | ${accounts}=  Salesforce Collection Insert  ${data}
        |
        | FOR  ${account}  IN  @{accounts}
        |     Set to dictionary  ${account}  Rating  Hot
        | END
        | Salesforce Collection Update  ${accounts}

        """
        for obj in objects:
            assert obj[
                "id"
            ], "Should be a list of objects with Ids returned by Salesforce Collection Insert"
            if STATUS_KEY in obj:
                del obj[STATUS_KEY]

        assert len(objects) <= SF_COLLECTION_INSERTION_LIMIT, (
            "Cannot update more than %s objects with this keyword"
            % SF_COLLECTION_INSERTION_LIMIT
        )

        records = self.cumulusci.sf.restful(
            "composite/sobjects",
            method="PATCH",
            json={"allOrNone": True, "records": objects},
        )

        for record, obj in zip(records, objects):
            obj[STATUS_KEY] = record

    def salesforce_query(self, obj_name, **kwargs):
        """Constructs and runs a simple SOQL query and returns a list of dictionaries.

        By default the results will only contain object Ids. You can
        specify a SOQL SELECT clase via keyword arguments by passing
        a comma-separated list of fields with the ``select`` keyword
        argument.

        Example:

        The following example searches for all Contacts where the
        first name is "Eleanor". It returns the "Name" and "Id"
        fields and logs them to the robot report:

        | @{records}=  Salesforce Query  Contact  select=Id,Name
        | FOR  ${record}  IN  @{records}
        |     log  Name: ${record['Name']} Id: ${record['Id']}
        | END

        """
        query = "SELECT "
        if "select" in kwargs:
            query += kwargs["select"]
        else:
            query += "Id"
        query += " FROM {}".format(obj_name)
        where = []
        for key, value in kwargs.items():
            if key == "select":
                continue
            where.append("{} = '{}'".format(key, value))
        if where:
            query += " WHERE " + " AND ".join(where)
        self.builtin.log("Running SOQL Query: {}".format(query))
        return self.cumulusci.sf.query_all(query).get("records", [])

    def salesforce_update(self, obj_name, obj_id, **kwargs):
        """ Updates a Salesforce object by Id.

        The keyword returns the result from the underlying
        simple_salesforce ``insert`` method, which is an HTTP
        status code. As with `Salesforce Insert`, field values
        are specified as keyword arguments.

        The following example assumes that ${contact id} has been
        previously set, and adds a Description to the given
        contact.

        | &{contact}=  Salesforce Update  Contact  ${contact id}
        | ...  Description=This Contact created during a test
        | Should be equal as numbers ${result}  204

        """
        self.builtin.log(
            "Updating {} {} with values {}".format(obj_name, obj_id, kwargs)
        )
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.update(obj_id, kwargs)

    def soql_query(self, query):
        """ Runs a simple SOQL query and returns the dict results

        The _query_ parameter must be a properly quoted SOQL query statement. The
        return value is a dictionary. The dictionary contains the keys
        as documented for the raw API call. The most useful key is ``records``,
        which contains a list of records which were matched by the query.

        Example

        The following example searches for all Contacts with a first
        name of "Eleanor" and a last name of "Rigby", and then prints
        the name of the first record found.

        | ${result}=  SOQL Query
        | ...  SELECT Name, Id FROM Contact WHERE FirstName='Eleanor' AND LastName='Rigby'
        | Run keyword if  len($result['records']) == 0  Fail  No records found
        |
        | ${contact}=  Get from list  ${result['records']}  0
        | Should be equal  ${contact['Name']}  Eleanor Rigby

        """
        self.builtin.log("Running SOQL Query: {}".format(query))
        return self.cumulusci.sf.query_all(query)

    def store_session_record(self, obj_type, obj_id):
        """ Stores a Salesforce record's Id for use in the *Delete Session Records* keyword.

        This keyword is automatically called by *Salesforce Insert*.
        """
        self.builtin.log("Storing {} {} to session records".format(obj_type, obj_id))
        self._session_records.append({"type": obj_type, "id": obj_id})

    @capture_screenshot_on_error
    def wait_until_modal_is_open(self):
        """ Wait for modal to open """
        self.selenium.wait_until_page_contains_element(
            lex_locators["modal"]["is_open"],
            timeout=15,
            error="Expected to see a modal window, but didn't",
        )

    def wait_until_modal_is_closed(self):
        """ Wait for modal to close """
        self.selenium.wait_until_page_does_not_contain_element(
            lex_locators["modal"]["is_open"], timeout=15
        )

    def wait_until_loading_is_complete(self, locator=None):
        """Wait for LEX page to load.

        (We're actually waiting for the actions ribbon to appear.)
        """
        locator = lex_locators["body"] if locator is None else locator
        try:
            self.selenium.wait_until_page_contains_element(locator)
            self.wait_for_aura()
            # this knowledge article recommends waiting a second. I don't
            # like it, but it seems to help. We should do a wait instead,
            # but I can't figure out what to wait on.
            # https://help.salesforce.com/articleView?id=000352057&language=en_US&mode=1&type=1
            time.sleep(1)

        except Exception:
            try:
                self.selenium.capture_page_screenshot()
            except Exception as e:
                self.builtin.warn("unable to capture screenshot: {}".format(str(e)))
            raise

    @capture_screenshot_on_error
    def wait_until_salesforce_is_ready(self, locator=None, timeout=None, interval=5):
        """Waits until we are able to render the initial salesforce landing page

        It will continue to refresh the page until we land on a
        lightning page or until a timeout has been reached. The
        timeout can be specified in any time string supported by robot
        (eg: number of seconds, "3 minutes", etc.). If not specified,
        the default selenium timeout will be used.

        This keyword will wait a few seconds between each refresh, as
        well as wait after each refresh for the page to fully render
        (ie: it calls wait_for_aura())

        """

        # Note: we can't just ask selenium to wait for an element,
        # because the org might not be availble due to infrastructure
        # issues (eg: the domain not being propagated). In such a case
        # the element will never come. Instead, what we need to do is
        # repeatedly refresh the page until the org responds.
        #
        # This assumes that any lightning page is a valid stopping
        # point.  If salesforce starts rendering error pages with
        # lightning, or an org's default home page is not a lightning
        # page, we may have to rethink that strategy.

        interval = 5  # seconds between each refresh.
        timeout = timeout if timeout else self.selenium.get_selenium_timeout()
        timeout_seconds = timestr_to_secs(timeout)
        start_time = time.time()
        login_url = self.cumulusci.login_url()
        locator = lex_locators["body"] if locator is None else locator

        while True:
            try:
                self.selenium.wait_for_condition(
                    "return (document.readyState == 'complete')"
                )
                self.wait_for_aura()

                # If the following doesn't throw an error, we're good to go.
                self.selenium.get_webelement(locator)
                break

            except Exception as e:
                self.builtin.log(
                    "caught exception while waiting: {}".format(str(e)), "DEBUG"
                )
                if time.time() - start_time > timeout_seconds:
                    self.selenium.log_location()
                    raise Exception("Timed out waiting for a lightning page")

            # known edge cases that can be worked around
            if self._check_for_login_failure():
                continue
            elif self._check_for_classic():
                continue

            # not a known edge case; take a deep breath and
            # try again.
            time.sleep(interval)
            self.selenium.go_to(login_url)

    def breakpoint(self):
        """Serves as a breakpoint for the robot debugger

        Note: this keyword is a no-op unless the debug option for
        the task has been set to True. Unless the option has been
        set, this keyword will have no effect on a running test.
        """
        return None

    def _check_for_classic(self):
        """Switch to lightning if we land on a classic page

        This seems to happen randomly, causing tests to fail
        catastrophically. The idea is to detect such a case and
        auto-click the "switch to lightning" link

        """
        try:
            # we don't actually want to wait here, but if we don't
            # explicitly wait, we'll implicitly wait longer than
            # necessary.  This needs to be a quick-ish check.
            self.selenium.wait_until_element_is_visible(
                "class:switch-to-lightning", timeout=2
            )
            self.builtin.log(
                "It appears we are on a classic page; attempting to switch to lightning",
                "WARN",
            )
            # this screenshot should be removed at some point,
            # but for now I want to make sure we see what the
            # page looks like if we get here.
            self.selenium.capture_page_screenshot()

            # just in case there's a modal present we'll try simulating
            # the escape key. Then, click on the switch-to-lightning link
            self.selenium.press_keys(None, "ESC")
            self.builtin.sleep("1 second")
            self.selenium.click_link("class:switch-to-lightning")
            return True

        except (NoSuchElementException, AssertionError):
            return False

    def _check_for_login_failure(self):
        """Handle the case where we land on a login screen

           Sometimes we get redirected to a login URL rather than
           being logged in, and we've yet to figure out precisely why
           that happens. Experimentation shows that authentication has
           already happened, so in this case we'll try going back to
           the instance url rather than the front door servlet.

           Admittedly, this is a bit of a hack, but it's better than
           never getting past this redirect.
        """

        location = self.selenium.get_location()
        if "//test.salesforce.com" in location or "//login.salesforce.com" in location:
            login_url = self.cumulusci.org.config["instance_url"]
            self.builtin.log(f"setting login_url temporarily to {login_url}", "DEBUG")
            self.selenium.go_to(login_url)
            return True
        return False
