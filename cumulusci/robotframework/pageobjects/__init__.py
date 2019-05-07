from robot.libraries.BuiltIn import BuiltIn
from .PageObjects import PageObjects  # noqa: F401
from .baseobjects import BasePage, ListingPage, HomePage, DetailPage  # noqa: F401


def pageobject(pageType, object_name=None):
    """A decorator to designate a class as a page object"""
    BuiltIn().log("importing page object {} {}".format(pageType, object_name), "DEBUG")

    def wrapper(cls):
        key = (pageType, object_name)
        PageObjects.registry[key] = cls
        if not hasattr(cls, "object_name"):
            cls.object_name = object_name
        return cls

    return wrapper
