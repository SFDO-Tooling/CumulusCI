import json
from .utam_element import element_factory


class UTAMBaseObject:
    def __init__(self, name, path=None):
        self.name = name
        # __name__ and __annotations__ are required by robot
        # to use an object as a keyword
        self.__annotations__ = self.__call__.__annotations__
        self.__name__ = name
        self.elements = []

        if path:
            with open(path, "r") as f:
                utam_definition = json.load(f)

            self.public = utam_definition.get("public", False)
            for element_def in utam_definition["elements"]:
                if element_def.get("public", False):
                    element = element_factory(element_def, self)
                    self.elements.append(element)
                    fnName = self._getter_name(element["name"])
                    setattr(self, fnName, element.getMyElement)

    def _getter_name(self, element_name):
        """Convert element name to a valid method name

        eg: foo -> getFoo; foo-bar: getFooBar, etc
        """
        element_name = element_name.replace("-", "_")
        getter_name = "get" + "".join(
            [word.title() for word in element_name.split("_")]
        )
        return getter_name

    def __call__(self, method, *args, **kwargs):
        # the first argument is expected to be the name of a getter.
        func = getattr(self, method, None)
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
            raise Exception(f"Unknown method name '{method}'. {message}")
        return func(*args, **kwargs)
