import re
import logging
from robot.libraries.BuiltIn import BuiltIn


class PageObject(object):
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    # These must be defined by subclasses
    PAGE_TYPE = None
    OBJECT_API_NAME = None

    """Base class to use for all page objects

    Derived classes should define PAGE_TYPE based on the appropriate
    pageReference type but with the "standard_" prefix removed (eg:
    objectPage rather than standard_objectPage)

    This class provides the following properties for accessing
    keywords in other libraries:

    builtin    - robot's built-in keywords (eg: self.builtin.log("..."))
    selenium   - SeleniumLibrary keywords
    salesforce - cumulusci.robotframework.Salesforce library
    cumulusci  - cumulusci.robotframework.CumulusCI library

    Derived classes can also define the following special methods:

    _go_to_tab

      called by the Salesforce keyword 'go to tab'. The default
      implementation will used the PAGE_TYPE and OBJECT_API_NAME
      attributes to construct a URL to the page. You can override
      this method to go to any URL you want.

    _is_current_page

      called by the keyword 'current page should be'. By default
      it will get the current page location and compare it to a
      URL based on the PAGE_TYPE and OBJECT_API_NAME attributes.

    """

    def __init__(self):
        # Turn off info logging of all http requests
        logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(
            logging.WARN
        )

    @property
    def builtin(self):
        """Returns an instance of robot framework's BuiltIn library"""
        return BuiltIn()

    @property
    def pagename(self):
        """Returns a readable form of the page object name

        A space is added before each string of one or more capital
        letters.  For example, 'SurfingSafariHomePage' will become
        'Surfing Safari Home Page'
        """
        return re.sub("(?!^)([A-Z][a-z]+)", r" \1", self.__class__.__name__)

    @property
    def cumulusci(self):
        """Returns the instance of the imported CumulusCI library"""
        return self.builtin.get_library_instance("cumulusci.robotframework.CumulusCI")

    @property
    def salesforce(self):
        """Returns the instance of the imported Salesforce library"""
        return self.builtin.get_library_instance("cumulusci.robotframework.Salesforce")

    @property
    def selenium(self):
        """Returns the instance of the imported SeleniumLibrary library"""
        return self.builtin.get_library_instance("SeleniumLibrary")

    def log_current_page_object(self):
        """Logs the current page object"""
        pobj = getattr(self.salesforce, "current_page_object", None)
        if pobj is not None:
            self.builtin.log(
                "current page object: {} ({})".format(
                    pobj.pagename, pobj.__class__.__name__
                )
            )
        else:
            self.builtin.log("current page object: None")
        self.selenium.capture_page_screenshot()

    def _go_to_tab(self):
        """Function called by the "go to tab" keyword

        Page objects can override this function if they want the keyword
        to go to a non-standard location based on the page type and object name.
        """
        if self.PAGE_TYPE == "objectPage":
            url_template = "{root}/lightning/o/{object_name}/home"
        else:
            raise Exception("Unknown page type '{}'".format(self.PAGE_TYPE))

        url = url_template.format(
            root=self.cumulusci.org.lightning_base_url, object_name=self.OBJECT_API_NAME
        )

        self.builtin.log("going to {}".format(url))
        self.selenium.go_to(url)
        self.salesforce.wait_until_loading_is_complete("css: ul.oneActionsRibbon")
        self.salesforce.set_current_page_object(self.__class__.__name__)
