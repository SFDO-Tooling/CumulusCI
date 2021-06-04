from robot.libraries.BuiltIn import BuiltIn
from robot.api.deco import keyword
from pathlib import Path
import os
import functools


class UTAMLibrary:
    def __init__(self, *names, paths=[]):
        for name in names:
            self.import_utam(name)
        here = Path(__file__).parent
        os.environ["UTAMPATH"] = ":".join([str(here / "resources")])

    @keyword(tags=["utam"])
    def import_utam(self, *names):
        """Create one or more UTAM page objects from their json definition

        This will create a keyword given by each of the names. In addition,
        it will create a location strategy for each as well.
        """
        for name in names:
            BuiltIn().import_library(
                "cumulusci.robotframework.utam.UTAM", name, "WITH NAME", f"UTAM:{name}"
            )
            selib = BuiltIn().get_library_instance("SeleniumLibrary")
            selib.add_location_strategy(
                name, functools.partial(self._locate_element, name=name)
            )

    def _locate_element(self, driver, locator, tag, constraints, name):
        # experiment to see how we can use a utam page object
        # as a locator strategy so that we can use utam locators with
        # utam-unaware keywords
        element = BuiltIn().run_keyword(name, locator)
        return element.getMyElement()
