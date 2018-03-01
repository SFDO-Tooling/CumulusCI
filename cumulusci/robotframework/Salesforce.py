import logging
from robot.libraries.BuiltIn import BuiltIn
from cumulusci.robotframework.selectors import selectors
from SeleniumLibrary.errors import ElementNotFound
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException

class Salesforce(object):
    def __init__(self, debug=False):
        self.debug = debug
        self.current_page = None
        self.selenium = BuiltIn().get_library_instance('SeleniumLibrary')
        self.cumulusci = BuiltIn().get_library_instance('cumulusci.robotframework.CumulusCI')
        # Turn off info logging of all http requests 
        logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARN)

    def current_app_should_be(self, app_name):
        locator = selectors['app_launcher']['current_app'].format(app_name)
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
            if e.message.contains('Other element would receive the click'):
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

    def open_app_launcher(self):
        locator = selectors['app_launcher']['button']
        self._call_selenium('_open_app_launcher', True, locator)

    def _open_app_launcher(self, locator):
        BuiltIn().log('Hovering over App Launcher button')
        self.selenium.mouse_over(locator)
        BuiltIn().log('Clicking App Launcher button')
        self.selenium.get_webelement(locator).click()
        BuiltIn().log('Waiting for modal to open')
        self.wait_until_modal_is_open()

    def select_app_launcher_app(self, app_name):
        locator = selectors['app_launcher']['app_link'].format(app_name)
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
        locator = selectors['app_launcher']['tab_link'].format(tab_name)
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
        BuiltIn().log('Deleting {} with Id {}'.format(obj_name, obj_id))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.delete(obj_id)

    def salesforce_get(self, obj_name, obj_id):
        BuiltIn().log('Getting {} with Id {}'.format(obj_name, obj_id))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.get(obj_id)

    def salesforce_insert(self, obj_name, **kwargs):
        BuiltIn().log('Inserting {} with values {}'.format(obj_name, kwargs))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        res = obj_class.create(kwargs)
        return res['id']

    def salesforce_query(self, obj_name, **kwargs):
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
        BuiltIn().log('Updating {} {} with values {}'.format(obj_name, obj_id, kwargs))
        obj_class = getattr(self.cumulusci.sf, obj_name)
        return obj_class.update(obj_id, kwargs)
        
    def soql_query(self, query):
        BuiltIn().log('Running SOQL Query: {}'.format(query))
        return self.cumulusci.sf.query_all(query)

    def wait_until_modal_is_open(self):
        self._call_selenium('_wait_until_modal_is_open', True)

    def _wait_until_modal_is_open(self):
        self.selenium.wait_until_element_is_visible(
            selectors['lex']['modal'],
        )

    def wait_until_modal_is_closed(self):
        self._call_selenium('_wait_until_modal_is_closed', True)

    def _wait_until_modal_is_closed(self):
        self.selenium.wait_until_element_is_not_visible(
            selectors['lex']['modal'],
        )

    def wait_until_loading_is_complete(self):
        self._call_selenium('_wait_until_loading_is_complete', True)

    def _wait_until_loading_is_complete(self):
        self.selenium.wait_until_element_is_not_visible(
            "css: div.auraLoadingBox.oneLoadingBox"
        )
        self.selenium.wait_until_page_contains_element(
            "css: div.desktop.container.oneOne.oneAppLayoutHost[data-aura-rendered-by]"
        )

    def _handle_page_load(self):
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
            
