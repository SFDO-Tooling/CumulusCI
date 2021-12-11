import importlib
import logging
import re
import time
from datetime import datetime
from pprint import pformat

import faker
from dateutil.parser import ParserError
from dateutil.parser import parse as parse_date
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from robot.utils import timestr_to_secs
from selenium.common.exceptions import (
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from SeleniumLibrary.errors import ElementNotFound, NoOpenBrowser
from simple_salesforce import SalesforceResourceNotFound
from urllib3.exceptions import ProtocolError

from cumulusci.core.template_utils import format_str
from cumulusci.robotframework import locator_manager
from cumulusci.robotframework.form_handlers import get_form_handler
from cumulusci.robotframework.utils import (
    capture_screenshot_on_error,
    get_locator_module_name,
    selenium_retry,
)

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
        """Initialize the Salesforce custom location strategies

        Note: This keyword is called automatically from *Open Test Browser*
        """

        if not self.builtin.get_variable_value(
            "${LOCATION STRATEGIES INITIALIZED}", False
        ):
            # this manages strategies based on locators in a dictionary
            locator_manager.register_locators("sf", lex_locators)
            locator_manager.add_location_strategies()

            # these are more traditional location strategies based on keywords
            # or functions
            self.selenium.add_location_strategy(
                "text", "Salesforce.Locate Element by Text"
            )
            self.selenium.add_location_strategy(
                "title", "Salesforce.Locate Element by Title"
            )
            self.selenium.add_location_strategy("label", self.locate_element_by_label)
            self.builtin.set_suite_variable("${LOCATION STRATEGIES INITIALIZED}", True)

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

    @capture_screenshot_on_error
    def scroll_element_into_view(self, locator):
        """Scroll the element identified by 'locator'

        This is a replacement for the keyword of the same name in
        SeleniumLibrary. The SeleniumLibrary implementation uses
        an unreliable method on Firefox. This keyword uses
        a more reliable technique.

        For more info see https://stackoverflow.com/a/52045231/7432
        """
        element = self.selenium.get_webelement(locator)
        self.selenium.driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'auto', block: 'center', inline: 'center'})",
            element,
        )

    @capture_screenshot_on_error
    def load_related_list(self, heading, tries=10):
        """Scrolls down until the specified related list loads.

        If the related list isn't found, the keyword will scroll down
        in 100 pixel increments to trigger lightning into loading the
        list. This process of scrolling will be repeated until the
        related list has been loaded or we've tried several times
        (the default is 10 tries)

        """
        locator = lex_locators["record"]["related"]["card"].format(heading)
        for i in range(tries):
            try:
                self.scroll_element_into_view(locator)
                return
            except (ElementNotFound, JavascriptException, WebDriverException):
                self.builtin.log(
                    f"related list '{heading}' not found; scrolling...", "DEBUG"
                )
            self.selenium.execute_javascript("window.scrollBy(0, 100)")
            self.wait_for_aura()
        raise AssertionError(f"Timed out waiting for related list '{heading}' to load.")

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
        """Closes the open modal"""
        locator = lex_locators["modal"]["close"]
        self._jsclick(locator)

    def current_app_should_be(self, app_name):
        """Validates the currently selected Salesforce App"""
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
        """Parses the current url to get the object id of the current record.
        Expects url format like: [a-zA-Z0-9]{15,18}
        """
        url = self.selenium.get_location()
        for part in url.split("/"):
            oid_match = re.match(OID_REGEX, part)
            if oid_match is not None:
                return oid_match.group(2)
        raise AssertionError("Could not parse record id from url: {}".format(url))

    def field_value_should_be(self, label, expected_value):
        """Verify that the form field for the given label is the expected value

        Example:

        | Field value should be    Account Name    ACME Labs
        """
        value = self.get_field_value(label)
        self.builtin.should_be_equal(value, expected_value)

    def get_field_value(self, label):
        """Return the current value of a form field based on the field label"""
        api_version = int(float(self.get_latest_api_version()))

        locator = self._get_input_field_locator(label)
        if api_version >= 51:
            # this works for both First Name (input) and Account Name (picklist)
            value = self.selenium.get_value(locator)
        else:
            # older releases it's a bit more complex
            element = self.selenium.get_webelement(locator)
            if element.get_attribute("role") == "combobox":
                value = self.selenium.get_text(f"sf:object.field_lookup_value:{label}")
            else:
                value = self.selenium.get_value(f"sf:object.field:{label}")

        return value

    def get_locator(self, path, *args, **kwargs):
        """Returns a rendered locator string from the Salesforce lex_locators
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
        """Navigates to the Home view of a Salesforce Object"""
        url = self.cumulusci.org.lightning_base_url
        url = "{}/lightning/o/{}/home".format(url, obj_name)
        self.selenium.go_to(url)
        self.wait_until_loading_is_complete(lex_locators["actions"])

    def go_to_object_list(self, obj_name, filter_name=None):
        """Navigates to the Home view of a Salesforce Object"""
        url = self.cumulusci.org.lightning_base_url
        url = "{}/lightning/o/{}/list".format(url, obj_name)
        if filter_name:
            url += "?filterName={}".format(filter_name)
        self.selenium.go_to(url)
        self.wait_until_loading_is_complete(lex_locators["actions"])

    def go_to_record_home(self, obj_id):
        """Navigates to the Home view of a Salesforce Object"""
        url = self.cumulusci.org.lightning_base_url
        url = "{}/lightning/r/{}/view".format(url, obj_id)
        self.selenium.go_to(url)
        self.wait_until_loading_is_complete(lex_locators["actions"])

    def go_to_setup_home(self):
        """Navigates to the Home tab of Salesforce Setup"""
        url = self.cumulusci.org.lightning_base_url
        self.selenium.go_to(url + "/lightning/setup/SetupOneHome/home")
        self.wait_until_loading_is_complete()

    def go_to_setup_object_manager(self):
        """Navigates to the Object Manager tab of Salesforce Setup"""
        url = self.cumulusci.org.lightning_base_url
        self.selenium.go_to(url + "/lightning/setup/ObjectManager/home")
        self.wait_until_loading_is_complete()

    def header_field_should_have_value(self, label):
        """Validates that a field in the record header has a text value.
        NOTE: Use other keywords for non-string value types
        """
        locator = lex_locators["record"]["header"]["field_value"].format(label)
        self.selenium.page_should_contain_element(locator)

    def header_field_should_not_have_value(self, label):
        """Validates that a field in the record header does not have a value.
        NOTE: Use other keywords for non-string value types
        """
        locator = lex_locators["record"]["header"]["field_value"].format(label)
        self.selenium.page_should_not_contain_element(locator)

    def header_field_should_have_link(self, label):
        """Validates that a field in the record header has a link as its value"""
        locator = lex_locators["record"]["header"]["field_value_link"].format(label)
        self.selenium.page_should_contain_element(locator)

    def header_field_should_not_have_link(self, label):
        """Validates that a field in the record header does not have a link as its value"""
        locator = lex_locators["record"]["header"]["field_value_link"].format(label)
        self.selenium.page_should_not_contain_element(locator)

    def click_header_field_link(self, label):
        """Clicks a link in record header."""
        locator = lex_locators["record"]["header"]["field_value_link"].format(label)
        self._jsclick(locator)

    def header_field_should_be_checked(self, label):
        """Validates that a checkbox field in the record header is checked"""
        locator = lex_locators["record"]["header"]["field_value_checked"].format(label)
        self.selenium.page_should_contain_element(locator)

    def header_field_should_be_unchecked(self, label):
        """Validates that a checkbox field in the record header is unchecked"""
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
        self.selenium.wait_until_element_is_visible("sf:app_launcher.view_all")
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
        """Enters a value into a lookup field."""
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
        self.wait_for_aura()

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
        field.send_keys(value)

    def _focus(self, element):
        """Set focus to an element

        In addition to merely setting the focus, we click the mouse
        to the field in case there are functions tied to that event.
        """
        self.selenium.set_focus_to_element(element)
        element.click()

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
        """Navigates to a Salesforce App via the App Launcher"""
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

        for idx, (record, obj) in enumerate(zip(records, objects)):
            if record["errors"]:
                raise AssertionError(
                    "Error on Object {idx}: {record} : {obj}".format(**vars())
                )

    def salesforce_query(self, obj_name, **kwargs):
        """Constructs and runs a simple SOQL query and returns a list of dictionaries.

        By default the results will only contain object Ids. You can
        specify a SOQL SELECT clause via keyword arguments by passing
        a comma-separated list of fields with the ``select`` keyword
        argument.

        You can supply keys and values to match against
        in keyword arguments, or a full SOQL where-clause
        in a keyword argument named ``where``. If you supply
        both, they will be combined with a SOQL "AND".

        ``order_by`` and ``limit`` keyword arguments are also
        supported as shown below.

        Examples:

        The following example searches for all Contacts where the
        first name is "Eleanor". It returns the "Name" and "Id"
        fields and logs them to the robot report:

        | @{records}=  Salesforce Query  Contact  select=Id,Name
        | ...          FirstName=Eleanor
        | FOR  ${record}  IN  @{records}
        |     log  Name: ${record['Name']} Id: ${record['Id']}
        | END

        Or with a WHERE-clause, we can look for the last contact where
        the first name is NOT Eleanor.

        | @{records}=  Salesforce Query  Contact  select=Id,Name
        | ...          where=FirstName!='Eleanor'
        | ...              order_by=LastName desc
        | ...              limit=1
        """
        query = self._soql_query_builder(obj_name, **kwargs)
        self.builtin.log("Running SOQL Query: {}".format(query))
        return self.cumulusci.sf.query_all(query).get("records", [])

    def _soql_query_builder(
        self, obj_name, select=None, order_by=None, limit=None, where=None, **kwargs
    ):
        query = "SELECT "
        if select:
            query += select
        else:
            query += "Id"
        query += " FROM {}".format(obj_name)
        where_clauses = []
        if where:
            where_clauses = [where]
        for key, value in kwargs.items():
            where_clauses.append("{} = '{}'".format(key, value))
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        if order_by:
            query += " ORDER BY " + order_by
        if limit:
            assert int(limit), "Limit should be an integer"
            query += f" LIMIT {limit}"

        return query

    def salesforce_update(self, obj_name, obj_id, **kwargs):
        """Updates a Salesforce object by Id.

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

    def soql_query(self, query, *args):
        """Runs a SOQL query and returns the result as a dictionary.

        The _query_ parameter must be a properly quoted SOQL query
        statement or statement fragment. Additional arguments will be
        joined to the query with spaces, allowing for a query to span
        multiple lines.

        This keyword will return a dictionary. The dictionary contains
        the keys as documented for the raw API call. The most useful
        keys are ``records`` and ``totalSize``, which contains a list
        of records that were matched by the query and the number of
        records that were returned.

        Example:

        The following example searches for all Contacts with a first
        name of "Eleanor" and a last name of "Rigby", and then logs
        the Id of the first record found.

        | ${result}=  SOQL Query
        | ...  SELECT Name, Id
        | ...  FROM   Contact
        | ...  WHERE  FirstName='Eleanor' AND LastName='Rigby'
        |
        | ${contact}=  Get from list  ${result['records']}  0
        | log  Contact Id: ${contact['Id']}

        """
        query = " ".join((query,) + args)
        self.builtin.log("Running SOQL Query: {}".format(query))
        return self.cumulusci.sf.query_all(query)

    def store_session_record(self, obj_type, obj_id):
        """Stores a Salesforce record's Id for use in the *Delete Session Records* keyword.

        This keyword is automatically called by *Salesforce Insert*.
        """
        self.builtin.log("Storing {} {} to session records".format(obj_type, obj_id))
        self._session_records.append({"type": obj_type, "id": obj_id})

    @capture_screenshot_on_error
    def wait_until_modal_is_open(self):
        """Wait for modal to open"""
        self.selenium.wait_until_page_contains_element(
            lex_locators["modal"]["is_open"],
            timeout=15,
            error="Expected to see a modal window, but didn't",
        )

    def wait_until_modal_is_closed(self):
        """Wait for modal to close"""
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

        Note: this keyword is a no-op unless the ``robot_debug`` option for
        the task has been set to ``true``. Unless the option has been
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

    def elapsed_time_for_last_record(
        self, obj_name, start_field, end_field, order_by, **kwargs
    ):
        """For records representing jobs or processes, compare the record's start-time to its end-time to see how long a process took.

        Arguments:
            obj_name:   SObject to look for last record
            start_field: Name of the datetime field that represents the process start
            end_field: Name of the datetime field that represents the process end
            order_by: Field name to order by. Should be a datetime field, and usually is just the same as end_field.
            where:  Optional Where-clause to use for filtering
            Other keywords are used for filtering as in the Salesforce Query keywordf

        The last matching record queried and summarized.

        Example:
            ${time_in_seconds} =    Elapsed Time For Last Record
            ...             obj_name=AsyncApexJob
            ...             where=ApexClass.Name='BlahBlah'
            ...             start_field=CreatedDate
            ...             end_field=CompletedDate
            ...             order_by=CompletedDate
        """
        if len(order_by.split()) != 1:
            raise Exception("order_by should be a simple field name")
        query = self._soql_query_builder(
            obj_name,
            select=f"{start_field}, {end_field}",
            order_by=order_by + " DESC NULLS LAST",
            limit=1,
            **kwargs,
        )
        response = self.soql_query(query)
        results = response["records"]

        if results:
            record = results[0]
            return _duration(record[start_field], record[end_field], record)
        else:
            raise Exception(f"Matching record not found: {query}")

    def start_performance_timer(self):
        """Start an elapsed time stopwatch for performance tests.

        See the docummentation for **Stop Performance Timer** for more
        information.

        Example:

            Start Performance Timer
            Do Something
            Stop Performance Timer
        """
        BuiltIn().set_test_variable("${__start_time}", datetime.now())

    def stop_performance_timer(self):
        """Record the results of a stopwatch. For perf testing.

        This keyword uses Set Test Elapsed Time internally and therefore
        outputs in all of the ways described there.

        Example:

            Start Performance Timer
            Do Something
            Stop Performance Timer

        """
        builtins = BuiltIn()

        start_time = builtins.get_variable_value("${__start_time}")
        if start_time:
            seconds = (datetime.now() - start_time).seconds
            assert seconds is not None
            self.set_test_elapsed_time(seconds)
        else:
            raise Exception(
                "Elapsed time clock was not started. "
                "Use the Start Elapsed Time keyword to do so."
            )

    def set_test_elapsed_time(self, elapsedtime):
        """This keyword captures a computed rather than measured elapsed time for performance tests.

        For example, if you were performance testing a Salesforce batch process, you might want to
        store the Salesforce-measured elapsed time of the batch process instead of the time measured
        in the CCI client process.

        The keyword takes a single argument which is either a number of seconds or a Robot time string
        (https://robotframework.org/robotframework/latest/libraries/DateTime.html#Time%20formats).

        Using this keyword will automatically add the tag cci_metric_elapsed_time to the test case
        and ${cci_metric_elapsed_time} to the test's variables. cci_metric_elapsed_time is not
        included in Robot's html statistical roll-ups.

        Example:

            Set Test Elapsed Time       11655.9

        Performance test times are output in the CCI logs and are captured in MetaCI instead of the
        "total elapsed time" measured by Robot Framework. The Robot "test message" is also updated."""

        builtins = BuiltIn()

        try:
            seconds = float(elapsedtime)
        except ValueError:
            seconds = timestr_to_secs(elapsedtime)
        assert seconds is not None

        builtins.set_test_message(f"Elapsed time set by test : {seconds}")
        builtins.set_tags("cci_metric_elapsed_time")
        builtins.set_test_variable("${cci_metric_elapsed_time}", seconds)

    def set_test_metric(self, metric: str, value=None):
        """This keyword captures any metric for performance monitoring.

        For example: number of queries, rows processed, CPU usage, etc.

        The keyword takes a metric name, which can be any string, and a value, which
        can be any number.

        Using this keyword will automatically add the tag cci_metric to the test case
        and ${cci_metric_<metric_name>} to the test's variables. These permit downstream
        processing in tools like CCI and MetaCI.

        cci_metric is not included in Robot's html statistical roll-ups.

        Example:

        | Set Test Metric    Max_CPU_Percent    30

        Performance test metrics are output in the CCI logs, log.html and output.xml.
        MetaCI captures them but does not currently have a user interface for displaying
        them."""

        builtins = BuiltIn()

        value = float(value)

        builtins.set_tags("cci_metric")
        builtins.set_test_variable("${cci_metric_%s}" % metric, value)

    @capture_screenshot_on_error
    def input_form_data(self, *args):
        """Fill in one or more labeled input fields fields with data

        Arguments should be pairs of field labels and values. Labels
        for required fields should not include the asterisk. Labels
        must be exact, including case.

        This keyword uses the keyword *Locate Element by Label* to
        locate elements. More details about how elements are found are
        in the documentation for that keyword.

        For most input form fields the actual value string will be
        used.  For a checkbox, passing the value "checked" will check
        the checkbox and any other value will uncheck it. Using
        "unchecked" is recommended for clarity.

        Example:

        | Input form data
        | ...  Opportunity Name         The big one       # required text field
        | ...  Amount                   1b                # currency field
        | ...  Close Date               4/01/2022         # date field
        | ...  Private                  checked           # checkbox
        | ...  Type                     New Customer      # combobox
        | ...  Primary Campaign Source  The Big Campaign  # picklist

        This keyword will eventually replace the "populate form"
        keyword once it has been more thoroughly tested in production.

        """

        it = iter(args)
        errors = []
        for label, value in list(zip(it, it)):
            # this uses our custom "label" locator strategy
            locator = f"label:{label}"
            # FIXME: we should probably only wait for the first label;
            # after that we can assume the fields have been rendered
            # so that we fail quickly if we can't find the element
            element = self.selenium.get_webelement(locator)
            handler = get_form_handler(element, locator)
            try:
                if handler:
                    handler.set(value)
                else:
                    raise Exception(
                        f"No form handler found for tag '{element.tag_name}'"
                    )
            except Exception as e:
                errors.append(f"{label}: {str(e)}")

        if errors:
            message = "There were errors with the following fields:\n"
            message += "\n".join(errors)
            raise Exception(message)

        # FIXME: maybe we should automatically set the focus to some
        # other element to trigger any event handlers on the last
        # element? But what should we set the focus to?

    def locate_element_by_label(self, browser, locator, tag, constraints):
        """Find a lightning component, input, or textarea based on a label

        If the component is inside a fieldset, the fieldset label can
        be prefixed to the label with a double colon in order to
        disambiguate the label.  (eg: Other address::First Name)

        If the label is inside nested ligntning components (eg:
        ``<lightning-input>...<lightning-combobox>...<label>``), the
        lightning component closest to the label will be
        returned (in this case, ``lightning-combobox``).

        If a lightning component cannot be found for the label, an
        attempt will be made to find an input or textarea associated
        with the label.

        This is registered as a custom locator strategy named "label"

        Example:

        The following example is for a form with a formset named
        "Expected Delivery Date", and inside of that a date input field
        with a label of "Date".

        These examples produce identical results:

        | ${element}=  Locate element by label    Expected Delivery Date::Date
        | ${element}=  Get webelement             label:Expected Delivery Date::Date

        """

        if "::" in locator:
            fieldset, label = [x.strip() for x in locator.split("::", 1)]
            fieldset_prefix = f'//fieldset[.//*[.="{fieldset}"]]'
        else:
            label = locator
            fieldset_prefix = ""

        xpath = fieldset_prefix + (
            # a label with the given text, optionally with a leading
            # or trailing "*" (ie: required field)
            f'//label[.="{label}" or .="*{label}" or .="{label}*"]'
            # then find the nearest ancestor lightning component
            '/ancestor::*[starts-with(local-name(), "lightning-")][1]'
        )
        elements = browser.find_elements_by_xpath(xpath)

        if not elements:
            # fall back to finding an input or textarea based on the 'for'
            # attribute of a label
            xpath = fieldset_prefix + (
                "//*[self::input or self::textarea]"
                f'[@id=string(//label[.="{label}" or .="*{label}" or .="{label}*"]/@for)]'
            )
            elements = browser.find_elements_by_xpath(xpath)

        return elements

    def select_window(self, locator="MAIN", timeout=None):
        """Alias for SeleniuimLibrary 'Switch Window'

        This keyword was removed from SeleniumLibrary 5.x, but some of our
        tests still use this keyword. You can continue to use this,
        but should replace any calls to this keyword with calls to
        'Switch Window' instead.
        """
        self.builtin.log(
            "'Select Window' is deprecated; use 'Switch Window' instead", "WARN"
        )
        self.selenium.switch_window(locator=locator, timeout=timeout)


def _duration(start_date: str, end_date: str, record: dict):
    try:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
    except (ParserError, TypeError) as e:
        raise Exception(f"Date parse error: {e} in record {record}")
    duration = end_date - start_date
    return duration.total_seconds()
