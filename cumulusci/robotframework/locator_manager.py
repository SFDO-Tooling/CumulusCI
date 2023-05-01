import functools
import re

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn
from SeleniumLibrary.errors import ElementNotFound

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
    """Register locators to be used with a custom locator strategy

    If the prefix is already known, the locators will be merged with
    the dictionary we already have.

    """
    if prefix in LOCATORS:
        logger.debug(f"merging keywords for prefix {prefix}")
        dictmerge(LOCATORS[prefix], locators)
    else:
        logger.debug(f"registering keywords for prefix {prefix}")
        LOCATORS[prefix] = locators


def add_location_strategies():
    """Call selenium's add_location_strategy keyword for all strategies"""

    # selenium throws an error if the location strategy already
    # exists, so we use a flag to make sure this code is called
    # only once.
    selenium = BuiltIn().get_library_instance("SeleniumLibrary")
    for (prefix, strategy) in LOCATORS.items():
        try:
            logger.debug(f"adding location strategy for '{prefix}'")
            selenium.add_location_strategy(
                prefix, functools.partial(locate_element, prefix)
            )
        except Exception as e:
            logger.debug(f"unable to register locators: {e}")


def locate_element(prefix, parent, locator, tag, constraints):
    """Translate a custom locator specification into an actual locator

    Our custom locators are of the form "p:x.y.z:a,b" where:

    - p is a short prefix (eg: sf, eda, sal),
    - x,y,z are keys to a locator dictionary (eg: locators['x']['y']['z'])
    - a,b are positional parameters passed to the string.format method
      when converting the custom locator into an actual locator

    A locator string (eg: locators['x']['y']['z']) can have substitution
    fields in it (eg: "a[@title='{}']"). These fields will be replaced
    with the positional parameters. It is possible for these fields to be
    named (eg: "a[@title='{title}'"), though we don't support named
    parameters.

    If the substitution fields are named, each unique name will be
    associated with a positional argument, in order. For example, if
    the arguments are "a,b" and if the locator string is something
    like "//{foo}|//{foo}/{bar}", then the first argument (a) will be
    assigned to the first namef field (foo) and the second argument (b)
    will be assigned to the second named field (bar).

    """

    selenium = BuiltIn().get_library_instance("SeleniumLibrary")
    loc = translate_locator(prefix, locator)
    logger.info(f"locator: '{prefix}:{locator}' => '{loc}'")

    try:
        elements = selenium.get_webelements(loc)
    except Exception as e:
        # The SeleniumLibrary documentation doesn't say, but I'm
        # pretty sure we should return an empty list rather than
        # throwing an error in this case. If we throw an error, that
        # prevents the custom locators from being used negatively (eg:
        # Page should not contain element custom:whatever).
        logger.debug(f"caught exception in locate_element: {e}")
        elements = []
    return elements


def translate_locator(prefix, locator):
    """Return the translated locator

    This uses the passed-in prefix and locator to find the
    proper element in the LOCATORS dictionary, and then formats it
    with any arguments that were part of the locator.

    See the docstring for `locate_element` for a description of how
    positional arguments are applied to named format fields.

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
            # this assumes that loc is a dictionary rather than a
            # string. If we've hit the leaf node of the locator and
            # there are still more keys, this will fail with a TypeError
            loc = loc[key.strip()]

    except (KeyError, TypeError):
        # TypeError: if the user passes in foo.bar.baz, but foo or foo.bar
        # resolves to a string rather than a nested dict.
        # KeyError if user passes in foo.bar and either 'foo' or 'bar' isn't
        # a valid key for a nested dictionary
        breadcrumb_path = ".".join(breadcrumbs)
        raise ElementNotFound(f"locator {prefix}:{breadcrumb_path} not found")

    if not isinstance(loc, str):
        raise TypeError(f"Expected locator to be of type string, but was {type(loc)}")

    try:
        # args is still a string, so split on ","
        # This means that arguments can't have commas in them, but I'm not sure
        # that will be a problem. If we find a case where it's a problem we can
        # do more sophisticated parsing.
        args = [arg.strip() for arg in argstring.split(",")] if argstring else []
        loc = apply_formatting(loc, args)
    except IndexError:
        raise Exception("Not enough arguments were supplied")
    return loc


def apply_formatting(locator, args):
    """Apply formatting to the locator

    If there are no named fields in the locator this is just a simple
    call to .format. However, some locators have named fields, and we
    don't support named arguments to keep the syntax simple, so we
    need to map positional arguments to named arguments before calling
    .format.

    Example:

    Given the locator "//*[a[@title='{title}'] or
    button[@name='{title}']]//{tag}" and args of ['foo', 'bar'], we'll
    pop 'foo' and 'bar' off of the argument list and assign them to
    the kwargs keys 'title' and 'tag'.

    """
    kwargs = {}
    for match in re.finditer(r"\{([^}]+)\}", locator):
        name = match.group(1)
        if name and name not in kwargs:
            kwargs[name] = args.pop(0)
    return locator.format(*args, **kwargs)
