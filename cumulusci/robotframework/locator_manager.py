from robot.libraries.BuiltIn import BuiltIn
import functools
from cumulusci.core.utils import dictmerge

"""
This module supports managing multiple location strategies. It
works like this:

0. Locators are stored in a global LOCATORS dictionary. The keys
   are the locator prefixes, the values are dictionaries containing
   the locators

1. Libraries can register a dictionary of locators with a prefix
   (eg: register_locators("npsp", {...})). These get added to
   LOCATORS

2. Open Test Browser calls selenium's add_location_strategy for each
   registered set of locators. (Note: Location strategies cannot be added before a
   browser is open).

3. Keywords can use dot notation to refer to locators. A colon
   separates the prefix from the locator, and a locator from a
   comma-separated string of arguments

Example:

    from a keyword library:

    | from cumulusci.robotframework.locator_manager import register_locators
    |
    | register_locators("example", {"dialog": {"button": "//button[text()='{}']"}})

    in a test:

    | page should contain element  example:dialog.button:Save

    ... will result in "//button[text()='Save']" being passed
    to 'page should contain element'

"""

LOCATORS = {}


def register_locators(prefix, locators):
    """Register a strategy with a set of locators or a keyword

    If the prefix is already known, merge in the new locators.
    """
    if prefix in LOCATORS:
        BuiltIn().log(f"merging keywords for prefix {prefix}", "DEBUG")
        dictmerge(LOCATORS[prefix], locators)
    else:
        BuiltIn().log(f"registering keywords for prefix {prefix}", "DEBUG")
        LOCATORS[prefix] = locators


def add_location_strategies():
    """Call selenium's add_location_strategy keyword for all strategies"""

    # selenium throws an error if the location strategy already
    # exists, so we use a flag to make sure this code is called
    # only once.
    selenium = BuiltIn().get_library_instance("SeleniumLibrary")
    for (prefix, strategy) in LOCATORS.items():
        try:
            BuiltIn().log(f"adding location strategy for '{prefix}'", "DEBUG")
            if isinstance(strategy, dict):
                selenium.add_location_strategy(
                    prefix, functools.partial(locate_element, prefix)
                )
            else:
                # not a dict? Just pass it through to selenium as-is
                # so that this function can register normal keywords
                selenium.add_location_strategy(prefix, strategy)
        except Exception as e:
            BuiltIn().log(f"unable to register locators: {e}", "DEBUG")


def locate_element(prefix, parent, locator, tag, constraints):
    """This is the function called by SeleniumLibrary when a custom locator
    strategy is used (eg: cci:foo.bar). We pass an additional argument,
    prefix, so we know which set of locators to use.

    This tokenizes the locator and then does a lookup in the dictionary associated
    with the given prefix. If any arguments are present, they are applied with
    .format() before being used to find an element.
    """

    # Ideally we should call get_webelements (plural) and filter
    # the results based on the tag and constraints arguments, but
    # the documentation on those arguments is virtually nil and
    # SeleniumLibrary's filter mechanism is a private function. In
    # practice it probably won't matter <shrug>.
    selenium = BuiltIn().get_library_instance("SeleniumLibrary")
    loc = translate_locator(prefix, locator)
    BuiltIn().log(f"locate_element: '{prefix}:{locator}' => {loc}", "DEBUG")
    try:
        element = selenium.get_webelement(loc)
    except Exception:
        raise Exception(
            f"Element with locator '{prefix}:{locator}' not found\ntranslated: '{loc}'"
        )
    return element


def translate_locator(prefix, locator):
    """Return the translated locator

    This uses the passed-in prefix and locator to find the
    proper element in the LOCATORS dictionary, and then formats it
    with any arguments that were part of the locator.

    """

    if ":" in locator:
        (path, argstring) = locator.split(":", 1)
    else:
        path = locator
        argstring = ""

    loc = LOCATORS[prefix]
    breadcrumbs = []
    try:
        for key in path.split("."):
            breadcrumbs.append(key)
            loc = loc[key.strip()]

    except KeyError:
        breadcrumb_path = ".".join(breadcrumbs)
        raise KeyError(f"locator {prefix}:{breadcrumb_path} not found")

    if not isinstance(loc, str):
        raise TypeError(f"Expected locator to be of type string, but was {type(loc)}")

    try:
        # args is still a string, so split on ","
        # This means that arguments can't have commas in them, but I'm not sure
        # that will be a problem. If we find a case where it's a problem we can
        # do more sophisticated parsing.
        args = [arg.strip() for arg in argstring.split(",")] if argstring else []
        loc = loc.format(*args)
    except IndexError:
        raise Exception("Not enough arguments were supplied")
    return loc
