from Browser import SupportedBrowsers

from cumulusci.robotframework.base_library import BaseLibrary


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

    def open_test_browser(self, size=None, useralias=None, recordVideo=None):
        """Open a new Playwright browser, context, and page to the default org.

        The return value is a tuple of the browser id, context id, and page details
        returned by the Playwright keywords New Browser, New Context, and New Page.

        This provides the most common environment for testing. For more control,
        you can create your own browser environment with the Browser library
        keywords `Create Browser`, `Create Context`, and `Create Page`.

        To record a video of the session, set `recordVideo` to True. The video
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
        if recordVideo:
            # ugh. the "dir" value must be non-empty, and will be treated as
            # a folder name under the browser/video folder. using "../video"
            # seems to be the only way to get the videos to go directly in
            # the video folder. Also, using "." doesn't work :-/
            recordVideo = {"dir": "../video"}
        width, height = size.split("x", 1)

        browser_id = self.browser.new_browser(browser=browser_enum, headless=headless)
        context_id = self.browser.new_context(
            viewport={"width": width, "height": height}, recordVideo=recordVideo
        )
        page_details = self.browser.new_page(login_url)

        self.browser.wait_until_network_is_idle()

        return browser_id, context_id, page_details
