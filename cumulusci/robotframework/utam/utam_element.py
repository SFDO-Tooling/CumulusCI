from robot.libraries.BuiltIn import BuiltIn


class Element(dict):
    def __init__(self, utam, parent, is_shadow=False):
        for prop in ("name", "selector"):
            if prop not in utam:
                raise Exception(
                    f"element definition missing required property '{prop}'"
                )

        super().__init__(utam)
        self.setdefault("nullable", False)
        self.setdefault("public", False)
        self.setdefault("type", None)
        self.elements = [
            element_factory(element_def, self)
            for element_def in utam.get("elements", [])
        ]
        shadow_elements = utam.get("shadow", {"elements": []})["elements"]
        self.shadow = {
            "elements": [
                element_factory(element_def, self, is_shadow=True)
                for element_def in shadow_elements
            ]
        }

    @property
    def selenium(self):
        return BuiltIn().get_library_instance("SeleniumLibrary")

    def __call__(self):
        return self.getMyElement()

    def getMyElement(self):
        selector = self["selector"]["css"]
        js = f"return document.querySelector('{selector}')"
        return self.selenium.execute_javascript(js)


class ActionableElement(Element):
    pass


class ClickableElement(ActionableElement):
    pass


class EditableElement(ClickableElement):
    pass


def element_factory(element_def, parent, is_shadow=False):
    """Create an appropriate element based on the type"""
    element_type_map = {
        None: Element,
        "actionable": ActionableElement,
        "clickable": ClickableElement,
        "editable": EditableElement,
    }
    element_type = element_def.get("type")
    cls = element_type_map[element_type]
    return cls(element_def, parent, is_shadow=is_shadow)
