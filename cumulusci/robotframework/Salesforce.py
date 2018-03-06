import logging
import re
from robot.libraries.BuiltIn import BuiltIn
from cumulusci.robotframework.locators import locators
from SeleniumLibrary.errors import ElementNotFound
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException

OID_REGEX = r'[a-zA-Z0-9]{15,18}'

class Salesforce(object):
    def __init__(self, debug=False):
        self.debug = debug
        self.current_page = None
        self.selenium = BuiltIn().get_library_instance('SeleniumLibrary')
        self.cumulusci = BuiltIn().get_library_instance('cumulusci.robotframework.CumulusCI')
        # Turn off info logging of all http requests 
        logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARN)

    def current_app_should_be(self, app_name):
        """ EXPERIMENTAL!!! """
        locator = locators['app_launcher']['current_app'].format(app_name)
        elem = self.selenium.set_focus_to_element(locator)
        elem = self.selenium.get_webelement(locator)
        assert app_name == elem.text

    def _call_selenium(self, method_name, retry, *args, **kwargs):
        """ A wrapper that catches common exceptions and handles them """
        exception = None
        retry_call = False

        # If at a new url, call self._handle_current_page() to inject JS into
        # the page to handle Lightning events
        current_page = self.selenium.get_location()
        if current_page != self.current_page:
            self.current_page = current_page
            self._handle_page_load()

        try:
            self._wait_until_loading_is_complete()
            method = getattr(self, method_name)
            method(*args, **kwargs)
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
            BuiltIn().log('Retrying call to method {}'.format(method_name), level='WARN')
            self._call_selenium(method_name, False, *args, **kwargs)

    def click_object_button(self, title):
        locator = locators['object']['button'].format(title)
        self._call_selenium('_click_object_button', True, locator)

    def _click_object_button(self, locator):
        button = self.selenium.get_webelement(locator)
        button.click()
        self._wait_until_modal_is_open()

    def click_modal_button(self, title):
        locator = locators['modal']['button'].format(title)
        self._call_selenium('_click_modal_button', True, locator)

    def _click_modal_button(self, locator):
        button = self.selenium.get_webelement(locator)
        button.click()

    def get_locator(self, path, *args, **kwargs):
        """ Returns a rendered locator string from the Salesforce locators
            dictionary.  This can be useful if you want to use an element in
            a different way than the built in keywords allow.
        """
        locator = locators
        for key in path.split('.'):
            locator = locator[key]
        return locator.format(*args, **kwargs)

    def get_current_record_id(self):
        """ Parses the current url to get the object id of the current record.
            Expects url format like: [a-zA-Z0-9]{15,18}
        """
        url = self.selenium.get_location()
        for part in url.split('/'):
            if re.match(OID_REGEX, part):
                return part
        raise AssertionError("Could not parse record id from url: {}".format(url))

    def header_field_should_have_value(self, label):
        """ Validates that a field in the record header has a text value.
            NOTE: Use other keywords for non-string value types
        """
        locator = locators['record']['header']['field_value'].format(label)
        self._call_selenium('_header_field_value_should_exist', True, locator)

    def header_field_should_not_have_value(self, label):
        """ Validates that a field in the record header does not have a value.
            NOTE: Use other keywords for non-string value types
        """
        locator = locators['record']['header']['field_value'].format(label)
        self._call_selenium('_header_field_value_should_not_exist', True, locator)

    def header_field_should_have_link(self, label):
        """ Validates that a field in the record header has a link as its value """
        locator = locators['record']['header']['field_value_link'].format(label)
        self._call_selenium('_header_field_value_should_exist', True, locator)
    
    def header_field_should_not_have_link(self, label):
        """ Validates that a field in the record header does not have a link as its value """
        locator = locators['record']['header']['field_value_link'].format(label)
        self._call_selenium('_header_field_value_should_not_exist', True, locator)

    def header_field_should_be_checked(self, label):
        """ Validates that a checkbox field in the record header is checked """
        locator = locators['record']['header']['field_value_checked'].format(label)
        self._call_selenium('_header_field_value_should_exist', True, locator)

    def header_field_should_be_unchecked(self, label):
        """ Validates that a checkbox field in the record header is unchecked """
        locator = locators['record']['header']['field_value_unchecked'].format(label)
        self._call_selenium('_header_field_value_should_exist', True, locator)

    def _header_field_value_should_exist(self, locator):
        self.selenium.page_should_contain_element(locator)
    
    def _header_field_value_should_not_exist(self, locator):
        self.selenium.page_should_not_contain_element(locator)

    def go_to_setup_home(self):
        """ Navigates to the Home tab of Salesforce Setup """
        url = self.cumulusci.org.lightning_base_url
        self.selenium.go_to(url + '/one/one.app#/setup/SetupOneHome/home')
        self._wait_until_loading_is_complete()

    def go_to_setup_object_manager(self):
        """ Navigates to the Object Manager tab of Salesforce Setup """
        url = self.cumulusci.org.lightning_base_url
        self.selenium.go_to(url + '/one/one.app#/setup/ObjectManager/home')
        self._wait_until_loading_is_complete()

    def go_to_object_home(self, obj_name):
        """ Navigates to the Home view of a Salesforce Object """
        url = self.cumulusci.org.lightning_base_url
        url = '{}/one/one.app#/sObject/{}/home'.format(url, obj_name)
        self.selenium.go_to(url)
        self._wait_until_loading_is_complete()
    
    def go_to_object_list(self, obj_name, filter_name=None):
        """ Navigates to the Home view of a Salesforce Object """
        url = self.cumulusci.org.lightning_base_url
        url = '{}/one/one.app#/sObject/{}/list'.format(url, obj_name)
        if filter_name:
            url += '?filterName={}'.format(filter_name)
        self.selenium.go_to(url)
        self._wait_until_loading_is_complete()

    def go_to_record_home(self, obj_id, filter_name=None):
        """ Navigates to the Home view of a Salesforce Object """
        url = self.cumulusci.org.lightning_base_url
        url = '{}/one/one.app#/sObject/{}/view'.format(url, obj_id)
        self.selenium.go_to(url)
        self._wait_until_loading_is_complete()

    def open_app_launcher(self):
        """ EXPERIMENTAL!!! """
        locator = locators['app_launcher']['button']
        self._call_selenium('_open_app_launcher', True, locator)

    def _open_app_launcher(self, locator):
        BuiltIn().log('Hovering over App Launcher button')
        self.selenium.mouse_over(locator)
        BuiltIn().log('Clicking App Launcher button')
        self.selenium.get_webelement(locator).click()
        BuiltIn().log('Waiting for modal to open')
        self.wait_until_modal_is_open()

    def populate_field(self, name, value):
        self._call_selenium('_populate_field', True, name, value)

    def _populate_field(self, name, value):
        locator = locators['object']['field'].format(name)
        field = self.selenium.get_webelement(locator)
        field.clear()
        field.send_keys(value)

    def populate_form(self, **kwargs):
        for name, value in kwargs.items():
            self._call_selenium('_populate_field', True, name, value)

    def select_record_type(self, label):
        self._wait_until_modal_is_open()
        locator = locators['object']['record_type_option'].format(label)
        self._call_selenium('_select_record_type', True, locator)

    def _select_record_type(self, locator):
        self.selenium.get_webelement(locator).click()
        locator = locators['modal']['button'].format('Next')
        self.selenium.click_button('Next')

    def select_app_launcher_app(self, app_name):
        """ EXPERIMENTAL!!! """
        locator = locators['app_launcher']['app_link'].format(app_name)
        BuiltIn().log('Opening the App Launcher')
        self.open_app_launcher()
        self._call_selenium('_select_app_launcher_app', True, locator)

    def _select_app_launcher_app(self, locator):
        BuiltIn().log('Getting the web element for the app')
        elem = self.selenium.set_focus_to_element(locator)
        elem = self.selenium.get_webelement(locator)
        BuiltIn().log('Getting the parent link from the web element')
        link = elem.find_element_by_xpath('../../..')
        self.selenium.set_focus_to_element(link)
        BuiltIn().log('Clicking the link')
        link.click()
        BuiltIn().log('Waiting for modal to close')
        self.wait_until_modal_is_closed()

    def select_app_launcher_tab(self, tab_name):
        """ EXPERIMENTAL!!! """
        locator = locators['app_launcher']['tab_link'].format(tab_name)
        BuiltIn().log('Opening the App Launcher')
        self.open_app_launcher()
        self._call_selenium('_select_app_launcher_tab', True, locator)

    def _select_app_launcher_tab(self, locator):
        BuiltIn().log('Clicking App Tab')
        self.selenium.set_focus_to_element(locator)
        self.selenium.get_webelement(locator).click()
        BuiltIn().log('Waiting for modal to close')
        self.wait_until_modal_is_closed()

    def salesforce_delete(self, obj_name, obj_id):
        """ Deletes a Saleforce object by id and returns the dict result """
        BuiltIn().log('Deleting {} with Id {}'.format(obj_name, obj_id))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.delete(obj_id)

    def salesforce_get(self, obj_name, obj_id):
        """ Gets a Salesforce object by id and returns the dict result """
        BuiltIn().log('Getting {} with Id {}'.format(obj_name, obj_id))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.get(obj_id)

    def salesforce_insert(self, obj_name, **kwargs):
        """ Inserts a Salesforce object setting fields using kwargs and returns the id """
        BuiltIn().log('Inserting {} with values {}'.format(obj_name, kwargs))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        res = obj_class.create(kwargs)
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
        BuiltIn().log('Running SOQL Query: {}'.format(query))
        return self.cumulusci.sf.query_all(query)

    def salesforce_update(self, obj_name, obj_id, **kwargs):
        """ Updates a Salesforce object by id and returns the dict results """
        BuiltIn().log('Updating {} {} with values {}'.format(obj_name, obj_id, kwargs))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.update(obj_id, kwargs)
        
    def soql_query(self, query):
        """ Runs a simple SOQL query and returns the dict results """
        BuiltIn().log('Running SOQL Query: {}'.format(query))
        return self.cumulusci.sf.query_all(query)

    def wait_until_modal_is_open(self):
        """ EXPERIMENTAL!!! """
        self._call_selenium('_wait_until_modal_is_open', True)

    def _wait_until_modal_is_open(self):
        self.selenium.wait_until_element_is_visible(
            locators['modal']['is_open'],
        )

    def wait_until_modal_is_closed(self):
        """ EXPERIMENTAL!!! """
        self._call_selenium('_wait_until_modal_is_closed', True)

    def _wait_until_modal_is_closed(self):
        self.selenium.wait_until_element_is_not_visible(
            locators['modal']['is_open'],
        )

    def wait_until_loading_is_complete(self):
        """ EXPERIMENTAL!!! """
        self._call_selenium('_wait_until_loading_is_complete', True)

    def _wait_until_loading_is_complete(self):
        self.selenium.wait_until_element_is_not_visible(
            "css: div.auraLoadingBox.oneLoadingBox"
        )
        self.selenium.wait_until_page_contains_element(
            "css: div.desktop.container.oneOne.oneAppLayoutHost[data-aura-rendered-by]"
        )

    def _handle_page_load(self):
        """ EXPERIMENTAL!!! """
        # Bypass this method for now and just return.  This is here as a prototype
        return
        self._wait_until_loading_is_complete()
        self.selenium.execute_javascript("""
            function cumulusciDoneRenderingHandler(e) {
                elements = $A.getComponent(e.source.getGlobalId()).getElements()
                if (elements.length > 0) {
                    elements[0].classList.add('cumulusci-done-rendering');
                }
            }
            $A.getRoot().addEventHandler('aura:doneRendering', cumulusciDoneRenderingHandler);
            """
        )
            
