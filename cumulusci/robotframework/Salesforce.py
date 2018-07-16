import logging
import re
import time
from robot.libraries.BuiltIn import BuiltIn
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.command import Command
from SeleniumLibrary.errors import ElementNotFound
from simple_salesforce import SalesforceMalformedRequest
from simple_salesforce import SalesforceResourceNotFound
from cumulusci.robotframework.locators import lex_locators

OID_REGEX = r'[a-zA-Z0-9]{15,18}'

# This is a list of user actions that are likely to trigger
# Aura actions and/or XHRs. We'll add a step to wait for
# in-flight XHRs to complete after these commands.
COMMANDS_INVOKING_ACTIONS = {
    Command.CLICK_ELEMENT,
}

# This script waits for a) Aura to be available and b)
# any in-flight Aura XHRs to be complete.
# We only do this if the page uses Aura, as determined by looking for
# id="auraAppcacheProgress" in the DOM.
# It would be nice if we could inject the function when the page loads
# and then just call it after commands, but I was having trouble
# getting webdriver to add it to the window scope.
WAIT_FOR_AURA_SCRIPT = """
done = arguments[0];
if (document.getElementById('auraAppcacheProgress')) {
    var waitForXHRs = function() {
        if (window.$A && !window.$A.clientService.inFlightXHRs()) {
            done();
        } else {
            setTimeout(waitForXHRs, 100);
        }
    }
    setTimeout(waitForXHRs, 0);
} else {
    done();
}
"""

class Salesforce(object):
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, debug=False):
        self.debug = debug
        self._session_records = []
        # Turn off info logging of all http requests 
        logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARN)

    @property
    def builtin(self):
        return BuiltIn()

    @property
    def cumulusci(self):
        return self.builtin.get_library_instance('cumulusci.robotframework.CumulusCI')

    @property
    def selenium(self):
        selenium = self.builtin.get_library_instance('SeleniumLibrary')

        # Patch the selenium webdriver to run the "wait for aura"
        # script after commands that are likely to invoke async actions.
        # (The problem with doing it this way is that it will
        # run even for actions that aren't on pages using Aura).
        if not getattr(selenium.driver, '_cumulus_patched', False):
            orig_execute = selenium.driver.execute
            def execute(driver_command, params=None):
                result = orig_execute(driver_command, params)
                if driver_command in COMMANDS_INVOKING_ACTIONS:
                    self._wait_for_aura()
                return result
            selenium.driver.execute = execute
            selenium.driver._cumulus_patched = True

        return selenium

    def current_app_should_be(self, app_name):
        """ EXPERIMENTAL!!! """
        locator = lex_locators['app_launcher']['current_app'].format(app_name)
        self.selenium.set_focus_to_element(locator)
        elem = self.selenium.get_webelement(locator)
        assert app_name == elem.text

    def _call_selenium(self, method_name, retry, *args, **kwargs):
        """ A wrapper that catches common exceptions and handles them """
        exception = None
        retry_call = False

        result = None
        try:
            method = getattr(self, method_name)
            result = method(*args, **kwargs)
        except ElementNotFound as e:
            # Retry once if we fail to find an element
            if retry is True:
                retry_call = True
            else:
                exception = e
        except StaleElementReferenceException as e:
            # Retry once if we encounter a stale element
            if retry is True:
                retry_call = True
            else:
                exception = e
        except WebDriverException as e:
            if 'Other element would receive the click' in e.message:
                if retry is True:
                    retry_call = True
                else:
                    exception = e
            else:
                exception = e
        except ElementNotInteractableException as e:
            if retry is True:
                retry_call = True
            else:
                exception = e
        except Exception as e:
            exception = e

        if exception:
            self.selenium.capture_page_screenshot()
            if self.debug:
                self.selenium.log_source()
                from cumulusci.robotframework.utils import set_pdb_trace
                set_pdb_trace()
                raise e
            else:
                raise e

        if retry_call:
            self.builtin.log('Retrying call to method {}'.format(method_name), level='WARN')
            return self._call_selenium(method_name, False, *args, **kwargs)

        return result

    def click_modal_button(self, title):
        locator = lex_locators['modal']['button'].format(title)
        self._call_selenium('_click_modal_button', True, locator)

    def _click_modal_button(self, locator):
        self.selenium.set_focus_to_element(locator)
        button = self.selenium.get_webelement(locator)
        button.click()

    def click_object_button(self, title):
        locator = lex_locators['object']['button'].format(title)
        self._call_selenium('_click_object_button', True, locator)

    def _click_object_button(self, locator):
        button = self.selenium.get_webelement(locator)
        button.click()
        self.wait_until_modal_is_open()

    def click_related_list_button(self, heading, button_title):
        locator = lex_locators['record']['related']['button'].format(heading, button_title)
        self._call_selenium('_click_related_list_button', True, locator)

    def _click_related_list_button(self, locator):
        self.selenium.set_focus_to_element(locator)
        self.selenium.get_webelement(locator).click()
        self.wait_until_modal_is_open()

    def delete_session_records(self):
        self._session_records.reverse()
        self.builtin.log('Deleting {} records'.format(len(self._session_records)))
        for record in self._session_records:
            self.builtin.log('  Deleting {type} {id}'.format(**record))
            try:
                self.salesforce_delete(record['type'], record['id'])
            except SalesforceResourceNotFound:
                self.builtin.log('    {type} {id} is already deleted'.format(**record))
            except SalesforceMalformedRequest as e:
                self.builtin.log('    {type} {id} could not be deleted:'.format(**record), level='WARN')
                self.builtin.log('      {}'.format(e), level='WARN')
        
    def get_current_record_id(self):
        """ Parses the current url to get the object id of the current record.
            Expects url format like: [a-zA-Z0-9]{15,18}
        """
        url = self.selenium.get_location()
        for part in url.split('/'):
            if re.match(OID_REGEX, part):
                return part
        raise AssertionError("Could not parse record id from url: {}".format(url))

    def get_locator(self, path, *args, **kwargs):
        """ Returns a rendered locator string from the Salesforce lex_locators
            dictionary.  This can be useful if you want to use an element in
            a different way than the built in keywords allow.
        """
        locator = lex_locators
        for key in path.split('.'):
            locator = locator[key]
        return locator.format(*args, **kwargs)

    def get_record_type_id(self, obj_type, developer_name):
        soql = "SELECT Id FROM RecordType WHERE SObjectType='{}' and DeveloperName='{}'".format(
            obj_type,
            developer_name,
        )
        res = self.cumulusci.sf.query_all(soql)
        return res['records'][0]['Id']

    def get_related_list_count(self, heading):
        locator = lex_locators['record']['related']['count'].format(heading)
        return self._call_selenium('_get_related_list_count', True, locator)

    def _get_related_list_count(self, locator):
        count = self.selenium.get_webelement(locator).text
        count = count.replace('(','').replace(')','')
        return int(count)
        
    def go_to_object_home(self, obj_name):
        """ Navigates to the Home view of a Salesforce Object """
        url = self.cumulusci.org.lightning_base_url
        url = '{}/one/one.app#/sObject/{}/home'.format(url, obj_name)
        self.selenium.go_to(url)
    
    def go_to_object_list(self, obj_name, filter_name=None):
        """ Navigates to the Home view of a Salesforce Object """
        url = self.cumulusci.org.lightning_base_url
        url = '{}/one/one.app#/sObject/{}/list'.format(url, obj_name)
        if filter_name:
            url += '?filterName={}'.format(filter_name)
        self.selenium.go_to(url)

    def go_to_record_home(self, obj_id, filter_name=None):
        """ Navigates to the Home view of a Salesforce Object """
        url = self.cumulusci.org.lightning_base_url
        url = '{}/one/one.app#/sObject/{}/view'.format(url, obj_id)
        self.selenium.go_to(url)

    def go_to_setup_home(self):
        """ Navigates to the Home tab of Salesforce Setup """
        url = self.cumulusci.org.lightning_base_url
        self.selenium.go_to(url + '/one/one.app#/setup/SetupOneHome/home')

    def go_to_setup_object_manager(self):
        """ Navigates to the Object Manager tab of Salesforce Setup """
        url = self.cumulusci.org.lightning_base_url
        self.selenium.go_to(url + '/one/one.app#/setup/ObjectManager/home')

    def header_field_should_have_value(self, label):
        """ Validates that a field in the record header has a text value.
            NOTE: Use other keywords for non-string value types
        """
        locator = lex_locators['record']['header']['field_value'].format(label)
        self._call_selenium('_header_field_value_should_exist', True, locator)

    def header_field_should_not_have_value(self, label):
        """ Validates that a field in the record header does not have a value.
            NOTE: Use other keywords for non-string value types
        """
        locator = lex_locators['record']['header']['field_value'].format(label)
        self._call_selenium('_header_field_value_should_not_exist', True, locator)

    def header_field_should_have_link(self, label):
        """ Validates that a field in the record header has a link as its value """
        locator = lex_locators['record']['header']['field_value_link'].format(label)
        self._call_selenium('_header_field_value_should_exist', True, locator)
    
    def header_field_should_not_have_link(self, label):
        """ Validates that a field in the record header does not have a link as its value """
        locator = lex_locators['record']['header']['field_value_link'].format(label)
        self._call_selenium('_header_field_value_should_not_exist', True, locator)

    def header_field_should_be_checked(self, label):
        """ Validates that a checkbox field in the record header is checked """
        locator = lex_locators['record']['header']['field_value_checked'].format(label)
        self._call_selenium('_header_field_value_should_exist', True, locator)

    def header_field_should_be_unchecked(self, label):
        """ Validates that a checkbox field in the record header is unchecked """
        locator = lex_locators['record']['header']['field_value_unchecked'].format(label)
        self._call_selenium('_header_field_value_should_exist', True, locator)

    def _header_field_value_should_exist(self, locator):
        self.selenium.page_should_contain_element(locator)
    
    def _header_field_value_should_not_exist(self, locator):
        self.selenium.page_should_not_contain_element(locator)

    def open_app_launcher(self):
        """ EXPERIMENTAL!!! """
        locator = lex_locators['app_launcher']['button']
        self._call_selenium('_open_app_launcher', True, locator)

    def _open_app_launcher(self, locator):
        self.builtin.log('Hovering over App Launcher button')
        self.selenium.mouse_over(locator)
        self.builtin.log('Clicking App Launcher button')
        self.selenium.get_webelement(locator).click()
        self.builtin.log('Waiting for modal to open')
        self.wait_until_modal_is_open()

    def populate_field(self, name, value):
        locator = lex_locators['object']['field'].format(name)
        self._call_selenium('_populate_field', True, locator, value)

    def populate_lookup_field(self, name, value):
        self.populate_field(name, value)
        locator = lex_locators['object']['field_lookup_value'].format(value)
        self._call_selenium('_populate_lookup_field', True, locator)
    
    def _populate_lookup_field(self, locator):
        self.selenium.set_focus_to_element(locator)
        self.selenium.get_webelement(locator).click()

    def _populate_field(self, locator, value):
        self.selenium.set_focus_to_element(locator)
        field = self.selenium.get_webelement(locator)
        field.clear()
        field.send_keys(value)

    def populate_form(self, **kwargs):
        for name, value in kwargs.items():
            locator = lex_locators['object']['field'].format(name)
            self._call_selenium('_populate_field', True, locator, value)

    def remove_session_record(self, obj_type, obj_id):
        try:
            self._session_records.remove({
                'type': obj_type,
                'id': obj_id,
            })
        except ValueError:
            self.builtin.log('Did not find record {} {} in the session records list'.format(obj_type, obj_id))

    def select_record_type(self, label):
        self.wait_until_modal_is_open()
        locator = lex_locators['object']['record_type_option'].format(label)
        self._call_selenium('_select_record_type', True, locator)

    def _select_record_type(self, locator):
        self.selenium.get_webelement(locator).click()
        locator = lex_locators['modal']['button'].format('Next')
        self.selenium.click_button('Next')

    def select_app_launcher_app(self, app_name):
        """ EXPERIMENTAL!!! """
        locator = lex_locators['app_launcher']['app_link'].format(app_name)
        self.builtin.log('Opening the App Launcher')
        self.open_app_launcher()
        self._call_selenium('_select_app_launcher_app', True, locator)

    def _select_app_launcher_app(self, locator):
        self.builtin.log('Getting the web element for the app')
        self.selenium.set_focus_to_element(locator)
        elem = self.selenium.get_webelement(locator)
        self.builtin.log('Getting the parent link from the web element')
        link = elem.find_element_by_xpath('../../..')
        self.selenium.set_focus_to_element(link)
        self.builtin.log('Clicking the link')
        link.click()
        self.builtin.log('Waiting for modal to close')
        self.wait_until_modal_is_closed()

    def select_app_launcher_tab(self, tab_name):
        """ EXPERIMENTAL!!! """
        locator = lex_locators['app_launcher']['tab_link'].format(tab_name)
        self.builtin.log('Opening the App Launcher')
        self.open_app_launcher()
        self._call_selenium('_select_app_launcher_tab', True, locator)

    def _select_app_launcher_tab(self, locator):
        self.builtin.log('Clicking App Tab')
        self.selenium.set_focus_to_element(locator)
        self.selenium.get_webelement(locator).click()
        self.builtin.log('Waiting for modal to close')
        self.wait_until_modal_is_closed()

    def salesforce_delete(self, obj_name, obj_id):
        """ Deletes a Saleforce object by id and returns the dict result """
        self.builtin.log('Deleting {} with Id {}'.format(obj_name, obj_id))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        res = obj_class.delete(obj_id)
        self.remove_session_record(obj_name, obj_id)

    def salesforce_get(self, obj_name, obj_id):
        """ Gets a Salesforce object by id and returns the dict result """
        self.builtin.log('Getting {} with Id {}'.format(obj_name, obj_id))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.get(obj_id)

    def salesforce_insert(self, obj_name, **kwargs):
        """ Inserts a Salesforce object setting fields using kwargs and returns the id """
        self.builtin.log('Inserting {} with values {}'.format(obj_name, kwargs))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        res = obj_class.create(kwargs)
        self.store_session_record(obj_name, res['id'])
        return res['id']

    def salesforce_query(self, obj_name, **kwargs):
        """ Constructs and runs a simple SOQL query and returns the dict results """
        query = 'SELECT '
        if 'select' in kwargs:
            query += kwargs['select']
        else:
            query += 'Id'
        query += ' FROM {}'.format(obj_name)
        where = []
        for key, value in kwargs.items():
            if key == 'select':
                continue
            where.append("{} = '{}'".format(key, value))
        if where:
            query += ' WHERE ' + ' AND '.join(where)
        self.builtin.log('Running SOQL Query: {}'.format(query))
        return self.cumulusci.sf.query_all(query).get('records', [])

    def salesforce_update(self, obj_name, obj_id, **kwargs):
        """ Updates a Salesforce object by id and returns the dict results """
        self.builtin.log('Updating {} {} with values {}'.format(obj_name, obj_id, kwargs))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.update(obj_id, kwargs)
        
    def soql_query(self, query):
        """ Runs a simple SOQL query and returns the dict results """
        self.builtin.log('Running SOQL Query: {}'.format(query))
        return self.cumulusci.sf.query_all(query)

    def store_session_record(self, obj_type, obj_id):
        """ Stores a Salesforce record's id for use in the Delete Session Records keyword """
        self.builtin.log('Storing {} {} to session records'.format(obj_type, obj_id))
        self._session_records.append({
            'type': obj_type,
            'id': obj_id,
        })

    def wait_until_modal_is_open(self):
        """ EXPERIMENTAL!!! """
        self._call_selenium('_wait_until_modal_is_open', True)

    def _wait_until_modal_is_open(self):
        self.selenium.wait_until_element_is_not_visible(
            lex_locators['spinner'],
            timeout=15,
        )
        self.selenium.wait_until_element_is_visible(
            lex_locators['modal']['is_open'],
            timeout=15,
        )

    def wait_until_modal_is_closed(self):
        """ EXPERIMENTAL!!! """
        self._call_selenium('_wait_until_modal_is_closed', True)

    def _wait_until_modal_is_closed(self):
        self.selenium.wait_until_element_is_not_visible(
            lex_locators['spinner'],
            timeout=15,
        )
        self.selenium.wait_until_element_is_not_visible(
            lex_locators['modal']['is_open'],
            timeout=15,
        )

    def wait_until_loading_is_complete(self):
        """ EXPERIMENTAL!!! """
        self._call_selenium('_wait_for_aura', True)

    def _wait_for_aura(self):
        """ EXPERIMENTAL!!!
        """
        self.selenium.driver.execute_async_script(WAIT_FOR_AURA_SCRIPT)
