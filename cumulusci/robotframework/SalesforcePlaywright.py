import re
import time

from Browser import SupportedBrowsers
from Browser.utils.data_types import KeyAction, PageLoadStates
from robot.utils import timestr_to_secs

from cumulusci.robotframework.base_library import BaseLibrary
from cumulusci.robotframework.faker_mixin import FakerMixin
from cumulusci.robotframework.utils import (
    WAIT_FOR_AURA_SCRIPT,
    capture_screenshot_on_error,
)


class SalesforcePlaywright(FakerMixin, BaseLibrary):
    ROBOT_LIBRARY_SCOPE = "Suite"

    def __init__(self):
        super().__init__()
        self._browser = None

    @property
    def browser(self):
        if self._browser is None:
            self._browser = self.builtin.get_library_instance("Browser")
        return self._browser

    def get_current_record_id(self):
        """Parses the current url to get the object id of the current record.
        This expects the url to contain an id that matches [a-zA-Z0-9]{15,18}
        """
        OID_REGEX = r"^(%2F)?([a-zA-Z0-9]{15,18})$"
        url = self.browser.evaluate_javascript(None, "window.location.href")
        for part in url.split("/"):
            oid_match = re.match(OID_REGEX, part)
            if oid_match is not None:
                return oid_match[2]
        raise AssertionError(f"Could not parse record id from url: {url}")

    def go_to_record_home(self, obj_id):
        """Navigates to the Home view of a Salesforce Object

        After navigating, this will wait until the slds-page-header_record-home
        div can be found on the page.
        """
        url = self.cumulusci.org.lightning_base_url
        url = f"{url}/lightning/r/{obj_id}/view"
        self.browser.go_to(url)
        self.wait_until_loading_is_complete("div.slds-page-header_record-home")

    def delete_records_and_close_browser(self):
        """This will close all open browser windows and then delete
        all records that were created with the Salesforce API during
        this testing session.
        """
        self.browser.close_browser("ALL")
        self.salesforce_api.delete_session_records()

    def open_test_browser(
        self, size=None, useralias=None, wait=True, record_video=None
    ):
        """Open a new Playwright browser, context, and page to the default org.

        The return value is a tuple of the browser id, context id, and page details
        returned by the Playwright keywords New Browser, New Context, and New Page.

        This provides the most common environment for testing. For more control,
        you can create your own browser environment with the Browser library
        keywords `Create Browser`, `Create Context`, and `Create Page`.

        To record a video of the session, set `record_video` to True. The video
        (*.webm) will be viewable in the log.html file at the point where this
        keyword is logged.

        This keyword automatically calls the browser keyword `Wait until network is idle`.
        """

        wait = self.builtin.convert_to_boolean(wait)
        default_size = self.builtin.get_variable_value(
            "${DEFAULT BROWSER SIZE}", "1280x1024"
        )
        size = size or default_size

        browser = self.builtin.get_variable_value("${BROWSER}", "chrome")
        headless = browser.startswith("headless")
        browser_type = browser[8:] if headless else browser
        browser_type = "chromium" if browser_type == "chrome" else browser_type
        browser_enum = getattr(SupportedBrowsers, browser_type, None)

        # Note: we can't just pass alias=useralias in the case of useralias being None.
        # That value gets passed to a salesforce query which barfs if the value
        # is None.
        login_url = (
            self.cumulusci.login_url(alias=useralias)
            if useralias
            else self.cumulusci.login_url()
        )

        if record_video:
            # ugh. the "dir" value must be non-empty, and will be treated as
            # a folder name under the browser/video folder. using "../video"
            # seems to be the only way to get the videos to go directly in
            # the video folder. Also, using "." doesn't work :-/
            record_video = {"dir": "../video"}
        width, height = size.split("x", 1)

        browser_id = self.browser.new_browser(browser=browser_enum, headless=headless)
        context_id = self.browser.new_context(
            viewport={"width": width, "height": height}, recordVideo=record_video
        )
        self.browser.set_browser_timeout("15 seconds")
        page_details = self.browser.new_page(login_url)

        if wait:
            self.wait_until_salesforce_is_ready(login_url)
        return browser_id, context_id, page_details

    @capture_screenshot_on_error
    def wait_until_loading_is_complete(self, locator=None, timeout="15 seconds"):
        """Wait for a lightning page to load.

        By default this keyword will wait for any element with the
        class 'slds-template__container', but a different locator can
        be provided.

        In addition to waiting for the element, it will also wait for
        any pending aura events to finish.

        """
        locator = (
            "//div[contains(@class, 'slds-template__container')]/*"
            if locator is None
            else locator
        )
        self.browser.get_elements(locator)

        self.browser.evaluate_javascript(None, WAIT_FOR_AURA_SCRIPT)
        # An old knowledge article recommends waiting a second. I don't
        # like it, but it seems to help. We should do a wait instead,
        # but I can't figure out what to wait on.
        time.sleep(1)

    @capture_screenshot_on_error
    def wait_until_salesforce_is_ready(
        self, login_url, locator=None, timeout="30 seconds"
    ):
        """Attempt to wait until we land on a lightning page

        In addition to waiting for a lightning page, this keyword will
        also attempt to wait until there are no more pending ajax
        requests.

        The timeout parameter is taken as a rough guideline. This
        keyword will actually wait for half of the timeout before
        starting checks for edge cases.

        """

        timeout_seconds = timestr_to_secs(timeout)
        start_time = time.time()

        locator = locator or "div.slds-template__container"
        expected_url = rf"/{self.cumulusci.org.lightning_base_url}\/lightning\/.*/"

        while True:
            try:
                # only wait for half of the timeout before doing some additional
                # checks. This seems to work better than one long timeout.
                self.browser.wait_for_navigation(
                    expected_url, timeout_seconds // 2, PageLoadStates.networkidle
                )
                self.wait_until_loading_is_complete(locator)
                # No errors? We're golden.
                break

            except Exception as exc:
                # dang. Maybe we landed somewhere unexpected?
                if self._check_for_classic():
                    continue

                if time.time() - start_time > timeout_seconds:
                    self.browser.take_screenshot()
                    raise Exception("Timed out waiting for a lightning page") from exc

            # If at first you don't succeed, ...
            self.browser.go_to(login_url)

    def _check_for_classic(self):
        """Switch to lightning if we land on a classic page

        This seems to happen randomly, causing tests to fail
        catastrophically. The idea is to detect such a case and
        auto-click the "switch to lightning" link

        """
        try:
            self.browser.get_element("a.switch-to-lightning")
            self.builtin.log(
                "It appears we are on a classic page; attempting to switch to lightning",
                "WARN",
            )
            # just in case there's a modal present we'll try simulating
            # the escape key. Then, click on the switch-to-lightning link
            self.browser.keyboard_key(KeyAction.press, "Escape")
            self.builtin.sleep("1 second")
            self.browser.click("a.switch-to-lightning")
            return True

        except AssertionError:
            return False

    @capture_screenshot_on_error
    def open_app_launcher(self, timeout="15 seconds"):
        """Opens the Salesforce App Launcher by clicking the waffle button.

        Waits for the App Launcher modal dialog to appear.
        """
        self.browser.click("button.slds-icon-waffle_container")
        self.wait_until_modal_is_open(timeout=timeout)

    @capture_screenshot_on_error
    def select_app_launcher_app(self, app_name, timeout="15 seconds"):
        """Searches for and selects an app in the App Launcher.

        Requires the App Launcher dialog to already be open.
        """
        search_input = "input[placeholder='Search apps and items...']"
        self.browser.fill_text(search_input, app_name)
        time.sleep(1)
        self.browser.click(f"a.slds-app-launcher__tile--small:has-text('{app_name}')")
        self.wait_until_loading_is_complete()

    @capture_screenshot_on_error
    def select_app_launcher_tab(self, tab_name, timeout="15 seconds"):
        """Searches for and selects a tab/item in the App Launcher.

        Requires the App Launcher dialog to already be open.
        """
        search_input = "input[placeholder='Search apps and items...']"
        self.browser.fill_text(search_input, tab_name)
        time.sleep(1)
        self.browser.click(f"one-app-launcher-menu-item a:has-text('{tab_name}')")
        self.wait_until_loading_is_complete()

    @capture_screenshot_on_error
    def populate_field(self, name, value):
        """Finds a form field by its label and fills it with the given value.

        ``name`` is the label text of the field.
        ``value`` is the text to enter.
        """
        input_el = f"lightning-input label:has-text('{name}')"
        try:
            self.browser.get_element(input_el)
            self.browser.fill_text(
                f"lightning-input:has(label:has-text('{name}')) input", value
            )
            return
        except (AssertionError, Exception):
            pass

        textarea_el = f"lightning-textarea:has(label:has-text('{name}')) textarea"
        try:
            self.browser.get_element(textarea_el)
            self.browser.fill_text(textarea_el, value)
            return
        except (AssertionError, Exception):
            pass

        generic = f"label:has-text('{name}')"
        self.browser.get_element(generic)
        self.browser.fill_text(
            f":near({generic}) input, :near({generic}) textarea", value
        )

    @capture_screenshot_on_error
    def populate_form(self, **kwargs):
        """Fills in multiple form fields at once.

        Each keyword argument maps a field label to its desired value.

        Example::

            Populate Form    First Name=Alice    Last Name=Smith
        """
        for name, value in kwargs.items():
            self.populate_field(name, value)

    @capture_screenshot_on_error
    def click_modal_button(self, button_text, timeout="15 seconds"):
        """Clicks a button with the given text inside the currently open modal dialog.

        Waits for the modal to be present first.
        """
        self.wait_until_modal_is_open(timeout=timeout)
        self.browser.click(
            f"div.slds-modal__container button:has-text('{button_text}')"
        )

    @capture_screenshot_on_error
    def wait_until_modal_is_open(self, timeout="15 seconds"):
        """Waits until a Salesforce modal dialog (``slds-modal``) is visible."""
        self.browser.wait_for_elements_state("section.slds-modal", "visible", timeout)

    @capture_screenshot_on_error
    def wait_until_modal_is_closed(self, timeout="15 seconds"):
        """Waits until all Salesforce modal dialogs (``slds-modal``) have disappeared."""
        self.browser.wait_for_elements_state("section.slds-modal", "detached", timeout)

    @capture_screenshot_on_error
    def click_related_list_button(self, heading, button_title):
        """Clicks a button within a related list identified by its heading.

        ``heading`` is the title text of the related list (e.g. "Contacts").
        ``button_title`` is the visible text of the button to click.
        """
        card = f"article.slds-card:has(span[title='{heading}'])"
        self.browser.click(f"{card} button:has-text('{button_title}')")

    @capture_screenshot_on_error
    def get_related_list_count(self, heading):
        """Returns the item count displayed in a related list's heading.

        ``heading`` is the title of the related list (e.g. "Contacts").
        Returns the integer count parsed from the heading, or 0 if no
        count is found.
        """
        span_text = self.browser.get_text(
            f"article.slds-card:has(span[title='{heading}']) "
            f"span.slds-card__header-title"
        )
        match = re.search(r"\((\d+)\)", span_text)
        if match:
            return int(match.group(1))
        return 0

    def breakpoint(self):
        """Serves as a breakpoint for the robot debugger

        Note: this keyword is a no-op unless the ``robot_debug`` option for
        the task has been set to ``true``. Unless the option has been
        set, this keyword will have no effect on a running test.
        """
        return None
