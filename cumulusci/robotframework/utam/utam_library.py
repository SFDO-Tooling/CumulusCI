"""
Load UTAM page objects

Page objects can be loaded with `Get UTAM Object` keyword. This will
dynamically create a new keyword named after the page object (eg:
`Get UTAM Object  lwc-home` creates a keyword named `lwc-home`.

Every page object can have nested elements. UTAM page objects will have
getters dynamically created for each public element
"""

from robot.libraries.BuiltIn import BuiltIn
from robot.errors import DataError
import robot.running.testlibraries
from cumulusci.robotframework.BaseLibrary import BaseLibrary
from pathlib import Path
from .utam_base import UTAMBaseObject


class UTAMLibrary(BaseLibrary):
    ROBOT_LIBRARY_SCOPE = "TEST"
    keywords = {}

    def __init__(self, *paths):
        super().__init__()
        self.utam_repositories = [
            Path(__file__).parent / "resources",
        ] + [Path(path) for path in paths]

        # this is a cache of all loaded keyword arguments
        # due to ROBOT_LIBRARY_SCOPE being set to "TEST", it should
        # get cleared out for every test, so objects won't bleed over
        # from one test to another.
        self.objects = {}

    def __getattr__(self, name):
        """Used by robot's dynamic library interface to find keyword implementations by name"""
        if name in self.objects:
            return self.objects[name]
        raise AttributeError(f"Unknown attribute '{name}'")

    def get_keyword_names(self):
        """Used by the robot hybrid library interface to get all keywords provided by this library"""

        keyword_names = ["get_utam_object"]
        keyword_names.extend(
            [utam_object.name for utam_object in self.objects.values()]
        )

        return keyword_names

    def get_utam_object(self, name):
        """Instantiate a UTAM page object and create a robot keyword"""
        utam_object = self.load_utam(name)
        self._refresh_keyword_list()
        return utam_object

    def load_utam(self, name):
        """Gets a UTAM page object by name

        This is not exposed as a keyword; it is designed for
        use by other python libraries to load objects without the
        overhead of creating them as keywords.
        """
        if name not in self.objects:
            path = self._find_utam_definition(name)
            self.objects[name] = UTAMBaseObject(name, path)
        return self.objects[name]

    def _find_utam_definition(self, name):
        """Returns the file path to the given page object"""
        for p in self.utam_repositories:
            path = p / f"{name}.utam.json"
            if path.exists():
                return path
        raise Exception(f"page object for '{name}' not found.")

    def _refresh_keyword_list(self):
        """Force robot to reload the keyword names from the library"""
        BuiltIn().reload_library(self)


# robot insists that keywords are methods or functions, not callable
# classes. This patches robot to accept callable classes.
def _validate_handler_method(self, method):
    # this probably needs to check that it is callable and that it
    # has a __name__ and __annotations__
    if not callable(method):
        raise DataError("Not a method or function.")
    if getattr(method, "robot_not_keyword", False) is True:
        raise DataError("Not exposed as a keyword.")
    return method


robot.running.testlibraries._BaseTestLibrary._validate_handler_method = (
    _validate_handler_method
)
