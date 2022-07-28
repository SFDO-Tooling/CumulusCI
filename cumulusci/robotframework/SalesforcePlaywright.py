import re

from Browser import SupportedBrowsers

from cumulusci.robotframework.base_library import BaseLibrary
from cumulusci.robotframework.faker_mixin import FakerMixin
from cumulusci.robotframework.utils import WAIT_FOR_AURA_SCRIPT


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

    def open_test_browser(self, size=None, useralias=None, record_video=None):
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
        page_details = self.browser.new_page(login_url)

        self.browser.wait_until_network_is_idle()

        return browser_id, context_id, page_details

    def wait_until_loading_is_complete(self, locator=None):
        """Wait for a lightning page to load.

        By default this keyword will wait for any element with the
        class 'slds-template__container', but a different locator can
        be provided.

        In addition to waiting for the element, it will also wait for
        any pending aura events, and it also calls the Browser keyword
        `Wait until network is idle`.

        """
        locator = (
            "//div[contains(@class, 'slds-template__container')]/*"
            if locator is None
            else locator
        )
        try:
            self.browser.get_element(locator)
            self.browser.execute_javascript(function=WAIT_FOR_AURA_SCRIPT)
            self.browser.wait_until_network_is_idle()

        except Exception:
            try:
                self.browser.take_screenshot()
            except Exception as e:
                self.builtin.warn("unable to capture screenshot: {}".format(str(e)))
            raise
