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
        url = self.browser.execute_javascript("window.location.href")
        for part in url.split("/"):
            oid_match = re.match(OID_REGEX, part)
            if oid_match is not None:
                return oid_match.group(2)
        raise AssertionError("Could not parse record id from url: {}".format(url))

    def go_to_record_home(self, obj_id):
        """Navigates to the Home view of a Salesforce Object

        After navigating, this will wait until the slds-page-header_record-home
        div can be found on the page.
        """
        url = self.cumulusci.org.lightning_base_url
        url = "{}/lightning/r/{}/view".format(url, obj_id)
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
        self.browser.execute_javascript(function=WAIT_FOR_AURA_SCRIPT)
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

            except Exception:
                # dang. Maybe we landed somewhere unexpected?
                if self._check_for_classic():
                    continue

                if time.time() - start_time > timeout_seconds:
                    self.browser.take_screenshot()
                    raise Exception("Timed out waiting for a lightning page")

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

        except (AssertionError):
            return False

    def breakpoint(self):
        """Serves as a breakpoint for the robot debugger

        Note: this keyword is a no-op unless the ``robot_debug`` option for
        the task has been set to ``true``. Unless the option has been
        set, this keyword will have no effect on a running test.
        """
        return None
