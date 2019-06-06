import glob
import importlib
import logging
import os.path
import re
import time
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from robot.utils import timestr_to_secs
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from simple_salesforce import SalesforceResourceNotFound
from cumulusci.robotframework.utils import selenium_retry
from SeleniumLibrary.errors import ElementNotFound, NoOpenBrowser
from urllib3.exceptions import ProtocolError

OID_REGEX = r"^(%2F)?([a-zA-Z0-9]{15,18})$"

lex_locators = {}  # will be initialized when Salesforce is instantiated


@selenium_retry
class Salesforce(object):
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

    def _init_locators(self):
        """Load the appropriate locator file for the current version

        If no version can be determined, we'll use the highest numbered
        locator file name.
        """
        try:
            client = self.cumulusci.tooling
            response = client._call_salesforce(
                "GET", "https://{}/services/data".format(client.sf_instance)
            )
            version = int(float(response.json()[-1]["version"]))
            locator_module_name = "locators_{}".format(version)

        except RobotNotRunningError:
            # We aren't part of a running test, likely because we are
            # generating keyword documentation. If that's the case we'll
            # use the latest supported version
            here = os.path.dirname(__file__)
            files = sorted(glob.glob(os.path.join(here, "locators_*.py")))
            locator_module_name = os.path.basename(files[-1])[:-3]

        self.locators_module = importlib.import_module(
            "cumulusci.robotframework." + locator_module_name
        )
        lex_locators.update(self.locators_module.lex_locators)

    @property
    def builtin(self):
        return BuiltIn()

    @property
    def cumulusci(self):
        return self.builtin.get_library_instance("cumulusci.robotframework.CumulusCI")

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

    def click_modal_button(self, title):
        """Clicks a button in a Lightning modal."""
        locator = lex_locators["modal"]["button"].format(title)
        self.selenium.click_button(locator)

    def click_object_button(self, title):
        """Clicks a button in an object's actions."""
        locator = lex_locators["object"]["button"].format(title)
        self.selenium.click_link(locator)
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
        self.selenium.click_link(locator)
        self.wait_until_modal_is_open()

    def click_related_item_link(self, heading, title):
        """Clicks a link in the related list with the specified heading."""
        self.load_related_list(heading)
        locator = lex_locators["record"]["related"]["link"].format(heading, title)
        self.selenium.click_link(locator)

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
        self.selenium.click_link(locator)
        locator = lex_locators["popup"]["link"].format(link)
        self.selenium.click_link(locator)

    def close_modal(self):
        """ Closes the open modal """
        locator = lex_locators["modal"]["close"]
        self.selenium.click_button(locator)

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
        self.selenium.click_link(locator)

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

    def open_app_launcher(self):
        """ Opens the Saleforce App Launcher """
        locator = lex_locators["app_launcher"]["button"]
        self.builtin.log("Clicking App Launcher button")
        self.selenium.click_button(locator)
        self.wait_until_modal_is_open()

    def populate_field(self, name, value):
        """Enters a value into a text field.

        Any existing value will be replaced.
        """
        locator = lex_locators["object"]["field"].format(name)
        self._populate_field(locator, value)

    def populate_lookup_field(self, name, value):
        """Enters a value into a lookup field.
        """
        input_locator = lex_locators["object"]["field"].format(name)
        menu_locator = lex_locators["object"]["field_lookup_link"].format(value)
        self.populate_field(name, value)
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
        self.selenium.get_webelement(menu_locator).click()

    def _populate_field(self, locator, value):
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
            locator = lex_locators["object"]["field"].format(name)
            self._populate_field(locator, value)

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
        self.selenium.get_webelement(locator).click()
        locator = lex_locators["modal"]["button"].format("Next")
        self.selenium.click_button("Next")

    def select_app_launcher_app(self, app_name):
        """Navigates to a Salesforce App via the App Launcher """
        locator = lex_locators["app_launcher"]["app_link"].format(app_name)
        self.builtin.log("Opening the App Launcher")
        self.open_app_launcher()
        self.builtin.log("Getting the web element for the app")
        self.selenium.set_focus_to_element(locator)
        elem = self.selenium.get_webelement(locator)
        self.builtin.log("Getting the parent link from the web element")
        link = elem.find_element_by_xpath("../../..")
        self.selenium.set_focus_to_element(link)
        self.builtin.log("Clicking the link")
        link.click()
        self.builtin.log("Waiting for modal to close")
        self.wait_until_modal_is_closed()

    def select_app_launcher_tab(self, tab_name):
        """Navigates to a tab via the App Launcher"""
        locator = lex_locators["app_launcher"]["tab_link"].format(tab_name)
        self.builtin.log("Opening the App Launcher")
        self.open_app_launcher()
        self.builtin.log("Clicking App Tab")
        self.selenium.set_focus_to_element(locator)
        self.selenium.get_webelement(locator).click()
        self.builtin.log("Waiting for modal to close")
        self.wait_until_modal_is_closed()

    def salesforce_delete(self, obj_name, obj_id):
        """ Deletes a Saleforce object by id and returns the dict result """
        self.builtin.log("Deleting {} with Id {}".format(obj_name, obj_id))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        obj_class.delete(obj_id)
        self.remove_session_record(obj_name, obj_id)

    def salesforce_get(self, obj_name, obj_id):
        """ Gets a Salesforce object by id and returns the dict result """
        self.builtin.log("Getting {} with Id {}".format(obj_name, obj_id))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.get(obj_id)

    def salesforce_insert(self, obj_name, **kwargs):
        """ Inserts a Salesforce object setting fields using kwargs and returns the id """
        self.builtin.log("Inserting {} with values {}".format(obj_name, kwargs))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        res = obj_class.create(kwargs)
        self.store_session_record(obj_name, res["id"])
        return res["id"]

    def salesforce_query(self, obj_name, **kwargs):
        """ Constructs and runs a simple SOQL query and returns the dict results """
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
        """ Updates a Salesforce object by id and returns the dict results """
        self.builtin.log(
            "Updating {} {} with values {}".format(obj_name, obj_id, kwargs)
        )
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.update(obj_id, kwargs)

    def soql_query(self, query):
        """ Runs a simple SOQL query and returns the dict results """
        self.builtin.log("Running SOQL Query: {}".format(query))
        return self.cumulusci.sf.query_all(query)

    def store_session_record(self, obj_type, obj_id):
        """ Stores a Salesforce record's id for use in the Delete Session Records keyword """
        self.builtin.log("Storing {} {} to session records".format(obj_type, obj_id))
        self._session_records.append({"type": obj_type, "id": obj_id})

    def wait_until_modal_is_open(self):
        """ Wait for modal to open """
        self.selenium.wait_until_page_contains_element(
            lex_locators["modal"]["is_open"], timeout=15
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
        except Exception:
            try:
                self.selenium.capture_page_screenshot()
            except Exception as e:
                self.builtin.warn("unable to capture screenshot: {}".format(str(e)))
            raise

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
                    self.selenium.capture_page_screenshot()
                    raise Exception("Timed out waiting for a lightning page")

            self.builtin.log("waiting for a refresh...", "DEBUG")
            self.selenium.capture_page_screenshot()
            time.sleep(interval)
            self.selenium.go_to(login_url)
