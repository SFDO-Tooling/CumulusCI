import time
import functools
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.command import Command
from SeleniumLibrary.errors import ElementNotFound


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
)


def selenium_retry(func):
    """Decorator to turn on selenium retry for a robot keyword.

    This is for use only with methods of a robotframework library
    that subclasses RetryingSeleniumLibraryMixin.
    """

    @functools.wraps(func)
    def run_with_retry(self, *args, **kwargs):
        # We keep track of the retry setting using a stack
        # so that multiple nested functions can use the decorator.
        # The stack is initialized lazily here.
        if not hasattr(self, "_retry_stack"):
            self._retry_stack = []
        self._retry_stack.append(True)
        try:
            return func(self, *args, **kwargs)
        except Exception:
            self.handle_selenium_exception()
        finally:
            self._retry_stack.pop()

    return run_with_retry


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
                retry_stack = getattr(self, "_retry_stack", [])
                retry_enabled = retry_stack and retry_stack[-1]
                try:
                    if retry_enabled:
                        # Retry certain failed commands once
                        result = self.selenium_execute_with_retry(
                            orig_execute, driver_command, params
                        )
                    else:
                        result = orig_execute(driver_command, params)
                except Exception:
                    self.handle_selenium_exception()

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

    def handle_selenium_exception(self):
        self.selenium.capture_page_screenshot()
        if self.debug:
            self.selenium.log_source()
            set_pdb_trace(pm=True)
        raise

    def wait_for_aura(self):
        """Run the WAIT_FOR_AURA_SCRIPT.

        This script polls Aura via $A in Javascript to determine when
        all in-flight XHTTP requests have completed before continuing.
        """
        self.selenium.driver.execute_async_script(WAIT_FOR_AURA_SCRIPT)
