import time
import functools
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException
from SeleniumLibrary.errors import ElementNotFound


def set_pdb_trace():
    import sys
    import pdb

    for attr in ("stdin", "stdout", "stderr"):
        setattr(sys, attr, getattr(sys, "__%s__" % attr))
    pdb.set_trace()


ALWAYS_RETRY_EXCEPTIONS = (
    ElementNotFound,
    ElementNotInteractableException,
    StaleElementReferenceException,
)


def selenium_retry(func):
    @functools.wraps(func)
    def deco_selenium_retry(self, *args, **kwargs):
        error = None
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            error = e
            retry = False
            if isinstance(e, ALWAYS_RETRY_EXCEPTIONS) or (
                isinstance(e, WebDriverException)
                and "Other element would receive the click" in str(e)
            ):
                retry = True
            if retry:
                self.builtin.log(
                    "Retrying call to method {}".format(func.__name__), level="WARN"
                )
                time.sleep(2)
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    error = e

        if error:
            self.selenium.capture_page_screenshot()
            if self.debug:
                self.selenium.log_source()
                set_pdb_trace()
            raise error

    return deco_selenium_retry
