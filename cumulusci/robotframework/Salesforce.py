from robot.libraries.BuiltIn import BuiltIn
from cumulusci.robotframework.selectors import selectors
from SeleniumLibrary.errors import ElementNotFound
from selenium.common.exceptions import StaleElementReferenceException

class Salesforce(object):
    def __init__(self, debug=False):
        self.debug = debug
        self.selenium = BuiltIn().get_library_instance('SeleniumLibrary')
        self.cumulusci = BuiltIn().get_library_instance('cumulusci.robotframework.CumulusCI')

    def current_app_should_be(self, app_name):
        locator = selectors['app_launcher']['current_app'].format(app_name)
        elem = self.selenium.set_focus_to_element(locator)
        elem = self.selenium.get_webelement(locator)
        assert app_name == elem.text

    def _call_selenium(self, method_name, retry, *args, **kwargs):
        """ A wrapper that catches common exceptions and handles them """
        #from cumulusci.robotframework.utils import set_pdb_trace; set_pdb_trace()
        exception = None
        retry_call = False
        try:
            self.wait_until_loading_is_complete()
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
        except Exception as e:
            exception = e

        if exception:
            self.selenium.capture_page_screenshot()
            self.selenium.log_source()
            if self.debug:
                from cumulusci.robotframework.utils import set_pdb_trace
                set_pdb_trace()
            else:
                raise e

        if retry_call:
            BuiltIn().log('Retrying call to method {}'.format(method_name), level='WARN')
            self._call_selenium(method_name, False, *args, **kwargs)

    def open_app_launcher(self):
        locator = selectors['app_launcher']['button']
        self._call_selenium('_open_app_launcher', True, locator)

    def _open_app_launcher(self, locator):
        BuiltIn().log('Focusing on App Launcher button')
        self.selenium.set_focus_to_element(locator)
        BuiltIn().log('Clicking App Launcher button')
        self.selenium.click_button(locator)
        try:
            BuiltIn().log('Waiting for modal to open')
            self.wait_until_modal_is_open()
        except:
            # Retry the click one time if the first click fails
            BuiltIn().log('Failed to open App Launcher, retrying the button click')
            self.selenium.click_button(locator)
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
        self.selenium.click_link(locator)
        BuiltIn().log('Waiting for modal to close')
        self.wait_until_modal_is_closed()

    def soql_query(self, query):
        return self.cumulusci.sf.query(query)

    def wait_until_modal_is_open(self):
        self.selenium.wait_until_element_is_visible(
            selectors['lex']['modal'],
        )

    def wait_until_modal_is_closed(self):
        self.selenium.wait_until_element_is_not_visible(
            selectors['lex']['modal'],
        )

    def wait_until_loading_is_complete(self):
        self.selenium.wait_until_element_is_not_visible(
            "css: div.auraLoadingBox.oneLoadingBox"
        )
        self.selenium.wait_until_page_contains_element(
            "css: div.desktop.container.oneOne.oneAppLayoutHost[data-aura-rendered-by]"
        )
