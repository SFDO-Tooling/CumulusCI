import re
import time

from Browser import SupportedBrowsers
from Browser.utils.data_types import ElementState
from robot.utils import timestr_to_secs

from cumulusci.robotframework.base_library import BaseLibrary
from cumulusci.robotframework.utils import WAIT_FOR_AURA_SCRIPT


class SalesforcePlaywright(BaseLibrary):
    ROBOT_LIBRARY_SCOPE = "Suite"

    def __init__(self):
        super().__init__()
        self._browser = None

    @property
    def browser(self):
        if self._browser is None:
            self._browser = self.builtin.get_library_instance("Browser")
        return self._browser

    def delete_records_and_close_browser(self):
        """This will close all open browser windows and then delete
        all records that were created with the Salesforce API during
        this testing session.
        """
        self.browser.close_browser("ALL")
        self.salesforce_api.delete_session_records()

    def open_test_browser(
        self, size=None, useralias=None, record_video=None, wait=True
    ):
        """Open a new Playwright browser, context, and page to the default org.

        The return value is a tuple of the browser id, context id, and page details
        returned by the Playwright keywords New Browser, New Context, and New Page.

        This provides the most common environment for testing. For more control,
        you can create your own browser environment with the Browser library
        keywords `Create Browser`, `Create Context`, and `Create Page`.

        To record a video of the session, set ``record_video`` to True. The video
        (*.webm) will be viewable in the log.html file at the point where this
        keyword is logged.

        This keyword automatically calls `Wait until Salesforce is ready` unless
        the ``wait`` parameter is set to false.
        """

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

        # browser's (or robot's?) automatic type conversion doesn't
        # seem to work when calling the function directly, so we have
        # to pass the enum rather than string representation of the
        # browser. _sigh_
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
        # this seems to fail randomly even with longer than average
        # timeouts. Simply trying again seems to make tests more stable.
        try:
            page_details = self.browser.new_page(login_url)
        except Exception:
            page_details = self.browser.new_page(login_url)

        if wait:
            self.wait_until_salesforce_is_ready()
        return browser_id, context_id, page_details

    def wait_until_salesforce_is_ready(
        self, locator="div.slds-template__container", timeout="30 seconds", interval=5
    ):
        """Waits until we are able to render the initial salesforce landing page

        It will continue to refresh the page until we land on a
        lightning page or until a timeout has been reached. The
        timeout can be specified in any time string supported by robot
        (eg: number of seconds, "3 minutes", etc.). If not specified,
        the default is 30 seconds.

        This keyword will wait a few seconds between each refresh, as
        well as wait after each refresh for the page to fully render.

        The keyword will attempt to detect when the browser opens up
        on a classic page, which seems to happen somewhat randomly. If
        it detects a classic page, it will attempt to visit the
        lightning/classic switcher URL and then go to the login
        screen.

        """

        timeout_seconds = timestr_to_secs(timeout)
        start_time = time.time()
        login_url = self.cumulusci.login_url()

        while True:
            self.browser.wait_for_function("document.readyState == 'complete'")
            self.browser.execute_javascript(function=WAIT_FOR_AURA_SCRIPT)

            # Is there a lightning component on the page? If so, consider
            # the page ready
            try:
                self.browser.get_element(locator)
                self.browser.wait_until_network_is_idle()
                break

            except Exception as e:
                self.builtin.log(
                    "caught exception while waiting: {}".format(str(e)), "DEBUG"
                )
                if time.time() - start_time > timeout_seconds:
                    raise Exception("Timed out waiting for a lightning page")

            if self._check_for_classic():
                # if _check_for_classic returns True, it found a
                # classic page and automatically hit the switcher URL
                # So, we'll go back through the loop and hope for the best.
                continue

            # not a known edge case; take a deep breath and
            # try again.
            time.sleep(interval)
            self.browser.go_to(login_url)

    def _check_for_classic(self):
        """Switch to lightning if we land on a classic page

        This seems to happen randomly, causing tests to fail
        catastrophically. The idea is to detect such a case and
        auto-click the "switch to lightning" link

        """
        try:
            self.browser.wait_for_elements_state(
                "a.switch-to-lightning", ElementState.visible, timeout="2 seconds"
            )
            self.builtin.log(
                "It appears we are on a classic page; attempting to switch to lightning",
                "WARN",
            )
            switcher_url = (
                self.cumulusci.org.config["instance_url"]
                + "/ltng/switcher?destination=lex"
            )
            self.browser.go_to(switcher_url)
            # give salesforce a chance to render
            self.builtin.sleep("5 seconds")
            return True

        except AssertionError as e:
            # unfortunately we can't be more precise with the exception, but
            # we can pull  out the error from the message string
            if e.args and re.search(
                r"TimeoutError.*a\.switch-to-lightning", e.args[0], re.DOTALL
            ):
                return False
            else:
                raise

        return False
