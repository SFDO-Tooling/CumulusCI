import os
import json
from pathlib import Path
from cumulusci.robotframework.utam import element_factory


class UTAM:
    """UTAM Page Object

    A new page object will be created from the definition in the
    given path. If no path is given, a filename will be computed
    and then searched for in UTAMPATH. The computed filename will
    be of the form "<name>.utam.json".

    When this class is instantiated, the instance will have getters
    created for every public element in the object definition. These
    getters will return web elements. The getters will be named
    after the element names, titlecased, and prefixed with "get"
    (eg: getHeader)

    A __call__ method has been defined so that an instance of this
    class can also be used as a keyword when the page object was
    created by the `import_utam` keyword in UTAMLibrary.

    """

    ROBOT_LIBRARY_SCOPE = "TEST"

    def __init__(self, name, path=None):
        """Create page object with given name

        If `path` is not given, search for a file by the name
        of <name>.utam.json in UTAMPATH
        """
        self.name = name
        self.__dict__[name] = self.__call__
        self.elements = []

        self.path = path if path else self._find_utam_definition(name)
        self._load()

    def __call__(self, element_name):
        getter = self._getter_name(element_name)
        func = getattr(self, getter, None)
        if func is None:
            if len(self.elements) > 1:
                method_names = [
                    self._getter_name(element["name"]) for element in self.elements
                ]
                message = f"Must be one of: {method_names}."
            elif len(self.elements) == 1:
                method_name = self._getter_name(self.elements[0]["name"])
                message = f"Must be '{method_name}'."
            else:
                message = ""
            raise Exception(f"Unknown element name '{element_name}'. {message}")
        return func

    def _load(self):
        """Read in the utam definition and create public element geters"""
        with open(self.path, "r") as f:
            utam_def = json.load(f)

            self.public = utam_def.get("public", False)

            # convert all elements to element objects
            for element_def in utam_def["elements"]:
                element = element_factory(element_def, self)
                self.elements.append(element)

            # create getters for all public elements
            for element in self._get_public_elements():
                getter_name = self._getter_name(element["name"])
                setattr(self, getter_name, element)

    def _get_public_elements(self, root=None):
        """Generator which returns all public elements"""
        for element in self.elements:
            if element.get("public", False):
                yield element
            for child_element in element.elements:
                if child_element.get("public", False):
                    yield child_element

    def _getter_name(self, element_name):
        """Convert element name to an appropriate method name

        The element name has dashes converted to underscores,
        then the words are capitalized, joined together, and
        prefixed with "get".

        Example: foo-bar becomes getFooBar
        """
        element_name = element_name.replace("-", "_")
        getter_name = "get" + "".join(
            [word.title() for word in element_name.split("_")]
        )
        return getter_name

    def _get_utampath(self):
        # This probably isn't right. We should probably predefine
        # some defaults which can be augmented with the env variable.
        if os.environ.get("UTAMPATH", None):
            utampath = [Path(path) for path in os.environ.get("UTAMPATH").split(":")]
            return utampath
        # maybe we want to return some reasonable default...?
        return []

    def _find_utam_definition(self, name):
        """Searches UTAMPATH for a file with the given name and returns the full path"""
        for p in self._get_utampath():
            path = p / f"{name}.utam.json"
            if path.exists():
                return p / path
        raise Exception(f"page object for '{name}' not found.")
