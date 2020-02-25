import functools
import time
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchWindowException
from selenium.webdriver.remote.command import Command
from SeleniumLibrary.errors import ElementNotFound
from robot.libraries.BuiltIn import BuiltIn


def set_pdb_trace(pm=False):
    """Start the Python debugger when robotframework is running.

    This makes sure that pdb can use stdin/stdout even though
    robotframework has redirected I/O.
    """
    import sys
    import pdb

    for attr in ("stdin", "stdout", "stderr"):
        setattr(sys, attr, getattr(sys, "__%s__" % attr))
    if pm:
        # Post-mortem debugging of an exception
        pdb.post_mortem()
    else:
        pdb.set_trace()


# This is a list of user actions that are likely to trigger
# Aura actions and/or XHRs. We'll add a step to wait for
# in-flight XHRs to complete after these commands.
COMMANDS_INVOKING_ACTIONS = {Command.CLICK_ELEMENT}


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


ALWAYS_RETRY_EXCEPTIONS = (
    ElementNotFound,
    ElementNotInteractableException,
    StaleElementReferenceException,
    NoSuchWindowException,
)


class RetryingSeleniumLibraryMixin(object):

    debug = False

    @property
    def selenium(self):
        selenium = self.builtin.get_library_instance("SeleniumLibrary")

        # Patch the selenium webdriver to add our own functionality
        # to improve stability.
        if not getattr(selenium.driver, "_cumulus_patched", False):
            orig_execute = selenium.driver.execute

            def execute(driver_command, params=None):
                try:
                    if self.retry_selenium:
                        # Retry certain failed commands once
                        result = self.selenium_execute_with_retry(
                            orig_execute, driver_command, params
                        )
                    else:
                        result = orig_execute(driver_command, params)
                except Exception:
                    if driver_command != Command.SCREENSHOT:
                        self.selenium.capture_page_screenshot()
                    if self.debug:
                        self.selenium.log_source()
                    raise

                # Run the "wait for aura" script after commands that are
                # likely to invoke async actions.
                if driver_command in COMMANDS_INVOKING_ACTIONS:
                    self.wait_for_aura()
                return result

            selenium.driver.execute = execute
            selenium.driver._cumulus_patched = True

        return selenium

    def selenium_execute_with_retry(self, execute, command, params):
        """Run a single selenium command and retry once.

        The retry happens for certain errors that are likely to be resolved
        by retrying.
        """
        try:
            return execute(command, params)
        except Exception as e:
            if isinstance(e, ALWAYS_RETRY_EXCEPTIONS) or (
                isinstance(e, WebDriverException)
                and "Other element would receive the click" in str(e)
            ):
                # Retry
                self.builtin.log("Retrying {} command".format(command), level="WARN")
                time.sleep(2)
                return execute(command, params)
            else:
                raise

    def wait_for_aura(self):
        """Run the WAIT_FOR_AURA_SCRIPT.

        This script polls Aura via $A in Javascript to determine when
        all in-flight XHTTP requests have completed before continuing.
        """
        try:
            self.selenium.driver.execute_async_script(WAIT_FOR_AURA_SCRIPT)
        except Exception:
            pass


def selenium_retry(target=None, retry=True):
    """Decorator to turn on automatic retries of flaky selenium failures.

    Decorate a robotframework library class to turn on retries for all
    selenium calls from that library::

        @selenium_retry
        class MyLibrary(object):

            # Decorate a method to turn it back off for that method
            @selenium_retry(False)
            def some_keyword(self):
                self.selenium.click_button('foo')

    Or turn it off by default but turn it on for some methods
    (the class-level decorator is still required)::

        @selenium_retry(False)
        class MyLibrary(object):

            @selenium_retry(True)
            def some_keyword(self):
                self.selenium.click_button('foo')
    """

    if isinstance(target, bool):
        # Decorator was called with a single boolean argument
        retry = target
        target = None

    def decorate(target):
        if isinstance(target, type):
            cls = target
            # Metaclass time.
            # We're going to generate a new subclass that:
            # a) mixes in RetryingSeleniumLibraryMixin
            # b) sets the initial value of `retry_selenium`
            return type(
                cls.__name__,
                (cls, RetryingSeleniumLibraryMixin),
                {"retry_selenium": retry, "__doc__": cls.__doc__},
            )
        func = target

        @functools.wraps(func)
        def run_with_retry(self, *args, **kwargs):
            # Set the retry setting and run the original function.
            old_retry = self.retry_selenium
            self.retry = retry
            try:
                return func(self, *args, **kwargs)
            finally:
                # Restore the previous value
                self.retry_selenium = old_retry

        run_with_retry.is_selenium_retry_decorator = True
        return run_with_retry

    if target is None:
        # Decorator is being used with arguments
        return decorate
    else:
        # Decorator was used without arguments
        return decorate(target)


def capture_screenshot_on_error(func):
    """Decorator for capturing a screenshot if a keyword throws an error

    The name is slightly misleading. While it was designed to capture a
    screenshot on error, it actually ties in to the same feature in
    SeleniumLibrary.

    SeleniumLibrary lets you define any keyword to be run on error,
    though I doubt we would ever use it for anything other than to
    capture screenshots. However, if you do configure SeleniumLibrary
    to do something other than (or in addition to) capturing a
    screenshot, any keyword that uses this decorator will behave just
    like a SeleniumLibrary keyword.

    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            selib = BuiltIn().get_library_instance("SeleniumLibrary")
            selib.failure_occurred()
            raise

    return wrapper
