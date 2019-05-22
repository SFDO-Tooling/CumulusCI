from robot.libraries.BuiltIn import BuiltIn
from .PageObjects import PageObjects  # noqa: F401
from .baseobjects import BasePage, ListingPage, HomePage, DetailPage  # noqa: F401


def pageobject(page_type, object_name=None):
    """A decorator to designate a class as a page object"""
    BuiltIn().log("importing page object {} {}".format(page_type, object_name), "DEBUG")

    def wrapper(cls):
        key = (page_type, object_name)
        PageObjects.registry[key] = cls
        if getattr(cls, "_object_name", None) is None:
            cls._object_name = object_name
        return cls

    return wrapper
