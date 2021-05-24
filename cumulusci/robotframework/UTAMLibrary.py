"""
Attempt to prove that I can add keywords to a library dynamically.

Unfortunately, get_keyword_names appears to be called exactly once
rather than every time a keyword is called. Kinda makes sense, but
it's a bummer.

Question: can I call 'import library' to force get_keyword_names
to be called again?

or what if I have a companion library that can be reloaded, but
which pulls its keywords from this library?

Note: from a UTAM presentation:
"every public element becomes public method that returns actionable UI element or other Page Object"
What's the difference between "page object" and "actionable UI element"?
Is the latter just a WebElement?

"""

from robot.libraries.BuiltIn import BuiltIn
from robot.errors import DataError
import robot.running.testlibraries
from cumulusci.robotframework.BaseLibrary import BaseLibrary
from pathlib import Path
import json
import types
import functools


class UTAMBaseObject(BaseLibrary):
    def __init__(self, name, path=None):
        self.name = name
        self.__annotations__ = self.__call__.__annotations__
        self._json = None
        self._method_names = []

        if path:
            with open(path, "r") as f:
                self._json = json.load(f)

            for element_def in self._json["elements"]:
                if element_def.get("public", False):
                    fnName = f"get{element_def['name'].title()}"
                    getElement = functools.partial(self._getElement, element_def, None)
                    getElement.__name__ = fnName
                    getElement.__doc__ = "get the element '{element_def['name']} / '{element_def['selector']}'"
                    setattr(self, fnName, types.MethodType(getElement, self))
                    self._method_names.append(fnName)

    def _getter_name(self, element_name):
        # foo -> getFoo; foo-bar: getFooBar
        element_name = element_name.replace("-", "_")
        getter_name = "get" + "".join(
            [word.title() for word in element_name.split("_")]
        )
        return getter_name

    def _getElement(self, element_def, *args, **kwargs):
        root_css = element_def["selector"]["css"]
        js = f"return document.querySelector('{root_css}')"
        return self.selenium.execute_javascript(js)

    def __name__(self):
        return self.name

    def __call__(self, method, *args, **kwargs):
        func = getattr(self, method, None)
        if func is None:
            if len(self._method_names) > 1:
                method_names = ",".join(self._method_names)
                message = f"Must be one of: {method_names}."
            elif len(self._method_names) == 1:
                message = f"Must be '{self._method_names[0]}'."
            else:
                message = ""
            raise Exception(f"Unknown method name '{method}'. {message}")
        return func(*args, **kwargs)


class UTAMLibrary(BaseLibrary):
    ROBOT_LIBRARY_SCOPE = "TEST"
    keywords = {}

    def __init__(self, *paths):
        super().__init__()
        self.utam_repositories = [
            Path(__file__).parent / "utam",
            Path("/Users/boakley/dev/utam-js-wdio-boilerplate/src/__utam__"),
        ] + [Path(path) for path in paths]

        try:
            self.selenium.add_location_strategy(
                "utam", self._locateElement, persist=True
            )
        except Exception as e:
            print("caught exception when registering locator strategy:", e)
            pass

    def __getattr__(self, name):
        if name in self.keywords:
            return self.keywords[name]
        else:
            raise AttributeError(f"Non-existing attribute {name}")

    def get_keyword_names(self):
        return [str(kw) for kw in self.keywords.keys()] + ["get_utam_object"]

    def get_utam_object(self, name):
        """Return an instance of UTAMBaseObject for the given keyword name"""
        if name not in self.keywords:
            for p in self.utam_repositories:
                path = p / f"{name}.utam.json"
                if path.exists():
                    self.keywords[name] = UTAMBaseObject(name, path)
                    try:
                        BuiltIn().reload_library(self)
                    except Exception:
                        print("I don't know why this is failing")
                    return self.keywords[name]
                else:
                    raise Exception(f"utam object definition not found: {name}")


# robot insists that keywords are methods or functions, not callable
# classes. This patches robot to accept callable classes
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
