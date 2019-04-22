import re

"""
Page Object management functions and keywords

The code in this mixin is for finding and loading the correct
page object for the current page.

"""


class PageObjectMixin(object):
    def current_page_should_be(self, name):
        """Verifies that the current page matches the given page object

        If the current page is what it's expected to be, the given page object
        will become the new current page.
        """
        po = self._get_page_object(name)
        if not po._is_current_page():
            self.selenium.capture_page_screenshot()
            raise Exception("The page '{}' is not the current page".format(name))
        self.set_current_page_object(name)

    def go_to_tab(self, name):
        """Go to the tab associated with the given page object name"""
        po = self._get_page_object(name)
        po._go_to_tab()

    def set_current_page_object(self, name):
        """This moves the given page object library to the start of the search order

        """
        po = self._get_page_object(name)
        self.builtin.log("setting page object to '{}'".format(str(po)), "DEBUG")

        self.builtin.set_library_search_order(po.__class__.__name__)
        self.current_page_object = po
        return po

    def _normalize_page_object_name(self, name, page_type="objectPage"):
        """Convert a page object reference into a library name.

        For the most part this just removes spaces: "Contact Home Page"
        becomes "ContactHomePage", etc.

        If you omit "Page", we'll attempt to add some missing
        parts. For example, we'll always append "Page".  Also, if it
        doesn't end in "Home Page", "List Page" or "New Page", we'll
        append "Home Page" instead of just "Page".

        For example, both "Contact" and "Contact Home" will be converted
        to "ContactHomePage".

        """

        name = name.strip()
        if re.match(r"^[^ ]+Page$", name):
            # No spaces and ends in Page? Leave it alone
            return name

        if re.match(r".*\s+(home|list|new)\s*$", name, flags=re.IGNORECASE):
            # ends with one of the supported actionNames
            name += " Page"

        elif not re.match(r".*\s+Page\s*$", name):
            if page_type == "objectPage":
                name += " Home Page"
            else:
                name += " Page"

        words = [
            word if word.isupper() else word.capitalize() for word in name.split(" ")
        ]
        normalized_name = "".join(words)
        self.builtin.log("{} normalized to {}".format(name, normalized_name), "DEBUG")
        return normalized_name

    def _get_page_object(self, name):
        normalized_name = self._normalize_page_object_name(name)

        try:
            # import it if it hasn't already been imported. Robot is smart
            # enough to cache libraries, so we don't have to worry too much
            # about performance.
            self.builtin.import_library(normalized_name)
            library = self.builtin.get_library_instance(normalized_name)
            return library

        except RuntimeError:
            # we'll get this error if we couldn't find a suitable class. In
            # such a case we'll instantiate a generic class and set its attributes
            # based on the requested page name

            # FIXME: At present this only works for object pages; it needs to be
            # expanded to handle other page types (Record page, Named Page, etc)
            match = re.search(
                r"(?P<objectname>.*?)(?P<pagename>(List|Home|New)Page)$",
                normalized_name,
            )
            if match:
                objectname = match.group("objectname")
                pagename = match.group("pagename")
                generic_normalized_name = "cumulusci.robotframework.Object{}".format(
                    pagename
                )

                self.builtin.import_library(
                    generic_normalized_name, "WITH NAME", normalized_name
                )
                library = self.builtin.get_library_instance(normalized_name)
                library.PAGE_TYPE = "objectPage"
                library.OBJECT_API_NAME = objectname
                self.builtin.log("Creating page object named '{}".format(name), "DEBUG")
                return library

            raise Exception("No page object by the name of '{}' found".format(name))
