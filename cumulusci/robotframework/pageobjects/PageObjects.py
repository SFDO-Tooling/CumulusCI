from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from cumulusci.robotframework.pageobjects.baseobjects import BasePage
import inspect
import robot.utils
import os
import sys


def get_keyword_names(obj):
    """Returns a list of method names for the given object

    This excludes methods that begin with an underscore, and
    also excludes the special method `get_keyword_names`.
    """
    names = [
        member[0]
        for member in inspect.getmembers(obj, inspect.isroutine)
        if (not member[0].startswith("_")) and member[0] != "get_keyword_names"
    ]
    return names


class PageObjects(object):
    """Keyword library for importing and using page objects

    When importing, you can include one or more paths to python
    files that define page objects. For example, if you have a set
    of classes in robot/HEDA/resources/PageObjects.py, you can import
    this library into a test case like this:

    | Library  cumulusci.robotframework.PageObjects
    | ...  robot/HEDA/resources/PageObjects.py

    """

    ROBOT_LIBRARY_SCOPE = "TEST SUITE"
    registry = {}
    cache = {}

    def __init__(self, *args):
        logger.debug("initializing PageObjects...")
        importer = robot.utils.Importer()

        for file_path in args:
            try:
                importer.import_class_or_module_by_path(os.path.abspath(file_path))
                logger.debug("imported page object {}".format(file_path))
            except Exception as e:
                logger.warn(str(e))
        self.current_page_object = None

        # Start with this library at the front of the library search order;
        # that may change as page objects are loaded.
        try:
            BuiltIn().set_library_search_order("PageObjects")
        except RobotNotRunningError:
            # this should only happen when trying to load this library
            # via the robot_libdoc task, in which case we don't care
            # whether this throws an error or not.
            pass

    @classmethod
    def _reset(cls):
        """Reset the internal data structures used to manage page objects

        This is to aid testing. It probably shouldn't be used at any other time.
        """
        for pobj in cls.registry.values():
            if pobj.__module__ in sys.modules:
                del sys.modules[pobj.__module__]
        cls.registry = {}
        cls.cache = {}

    @property
    def selenium(self):
        return BuiltIn().get_library_instance("SeleniumLibrary")

    def __getattr__(self, name):
        """Return the keyword from the current page object

        This method is required by robot's dynamic library api
        """
        if self.current_page_object is None:
            raise AttributeError(name)
        return getattr(self.current_page_object, name)

    def get_keyword_names(self):
        """
        This method is required by robot's dynamic library api
        """
        names = get_keyword_names(self)
        if self.current_page_object is not None:
            names = names + get_keyword_names(self.current_page_object)
        return names

    def log_page_object_keywords(self):
        """Logs page objects and their keywords for all page objects which have been imported"""
        for key in sorted(self.registry.keys()):
            pobj = self.registry[key]
            keywords = get_keyword_names(pobj)
            logger.info("{}: {}".format(key, ", ".join(keywords)))

    def _get_page_object(self, page_type, object_name):

        if (page_type, object_name) in self.cache:
            # have we already loaded this once? If so, our work here is done.
            pobj = self.cache[(page_type, object_name)]

        elif (page_type, object_name) in self.registry:
            # not in cache, but it's registered so create an instance
            cls = self.registry[(page_type, object_name)]
            pobj = cls()

        else:
            # not in cache, and not registered. Use a generic class
            target = "{}Page".format(page_type)
            pobj = None
            for subclass in BasePage.__subclasses__():
                if subclass.__name__ == target:
                    pobj = subclass(object_name)
                    break

        if pobj:
            self.cache[(page_type, object_name)] = pobj
        else:
            raise Exception(
                "Unable to find a page object for '{} {}'".format(
                    page_type, object_name
                )
            )

        return pobj

    def go_to_page(self, page_type, object_name, **kwargs):
        """Go to the page of the given page object.

        Different pages support different additional arguments. For
        example, a Listing page supports the keyword argument `filter_name`.

        If this keyword is able to navigate to a page, the keywords for
        this page object will be loaded.
        """

        pobj = self._get_page_object(page_type, object_name)
        try:
            pobj._go_to_page(**kwargs)
        except Exception:
            self.selenium.capture_page_screenshot()
            raise

    def current_page_should_be(self, page_type, object_name, **kwargs):
        """Verifies that the page appears to be the requested page

        If this is the expected page, the keywords for this page
        object will be loaded.
        """
        pobj = self._get_page_object(page_type, object_name)
        try:
            pobj._is_current_page(**kwargs)
            self.load_page_object(page_type, object_name)
        except Exception:
            self.selenium.capture_page_screenshot()
            raise

    def load_page_object(self, page_type, object_name=None):
        """Load the keywords for the page object identified by the type and object name

        The page type / object name pair must have been registered
        using the cumulusci.robotframework.pageobject decorator.
        """
        pobj = self._get_page_object(page_type, object_name)
        self._set_current_page_object(pobj)
        return pobj

    def _set_current_page_object(self, pobj):
        """This does the work of importing the keywords for the given page object"""

        # Note: at the moment only one object is loaded at a time. We might want
        # to consider pushing and popping page objects on a stack so that more than
        # one can be active at a time.
        self.current_page_object = pobj
        libname = self.current_page_object.__class__.__name__

        # rename this library to be the name of our page object,
        # and make sure it is at the front of the library search order
        BuiltIn()._namespace._kw_store.get_library(self).name = libname
        BuiltIn().reload_library(self)
        BuiltIn().set_library_search_order(libname)
        return pobj
