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

ALWAYS_RETRY_EXCEPTIONS=(
    ElementNotFound,
    ElementNotInteractableException,
    StaleElementReferenceException,
)

def selenium_retry(func):
    @functools.wraps(func)
    def deco_selenium_retry(*args, **kwargs):
        retry = False
        try:
            return func(*args, **kwargs)
        except ALWAYS_RETRY_EXCEPTIONS as e:
            retry = True
        except WebDriverException as e:
            if "Other element would receive the click" in e.msg:
                retry = True
        except Exception as e:
            pass
        if retry:
            args[0].builtin.log(
                "Retrying call to method {}".format(func.__name__), level="WARN" 
            )
            time.sleep(2)
            return func(*args, **kwargs) 
        else:
            args[0].selenium.capture_page_screenshot()
            if args[0].debug:
                args[0].selenium.log_source()
                set_pdb_trace()
            raise(e)

    return deco_selenium_retry