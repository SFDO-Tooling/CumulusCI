import logging
import re
import time
from robot.libraries.BuiltIn import BuiltIn
from selenium.webdriver.common.keys import Keys
from simple_salesforce import SalesforceMalformedRequest
from simple_salesforce import SalesforceResourceNotFound
from cumulusci.robotframework.locators import lex_locators
from cumulusci.robotframework.utils import selenium_retry
from SeleniumLibrary.errors import ElementNotFound

OID_REGEX = r"[a-zA-Z0-9]{15,18}"


@selenium_retry
class Salesforce(object):
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, debug=False):
        self.debug = debug
        self._session_records = []
        # Turn off info logging of all http requests
        logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(
            logging.WARN
        )

    @property
    def builtin(self):
        return BuiltIn()

    @property
    def cumulusci(self):
        return self.builtin.get_library_instance("cumulusci.robotframework.CumulusCI")

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
            self.selenium.execute_javascript(
                "window.scrollTo(0,document.body.scrollHeight)"
            )
            self.wait_for_aura()
            try:
                el = self.selenium.get_webelement(locator)
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
        for record in self._session_records:
            self.builtin.log("  Deleting {type} {id}".format(**record))
            try:
                self.salesforce_delete(record["type"], record["id"])
            except SalesforceResourceNotFound:
                self.builtin.log("    {type} {id} is already deleted".format(**record))
            except SalesforceMalformedRequest as e:
                self.builtin.log(
                    "    {type} {id} could not be deleted:".format(**record),
                    level="WARN",
                )
                self.builtin.log("      {}".format(e), level="WARN")

    def get_current_record_id(self):
        """ Parses the current url to get the object id of the current record.
            Expects url format like: [a-zA-Z0-9]{15,18}
        """
        url = self.selenium.get_location()
        for part in url.split("/"):
            if re.match(OID_REGEX, part):
                return part
        raise AssertionError("Could not parse record id from url: {}".format(url))

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
        self.selenium.set_focus_to_element(locator)
        field = self.selenium.get_webelement(locator)
        field.send_keys(Keys.HOME + Keys.SHIFT + Keys.END)
        field.send_keys(value)

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
        res = obj_class.delete(obj_id)
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

    def wait_until_loading_is_complete(self, locator=lex_locators["body"]):
        """Wait for LEX page to load.

        (We're actually waiting for the actions ribbon to appear.)
        """
        self.selenium.wait_until_page_contains_element(locator)
        self.wait_for_aura()
