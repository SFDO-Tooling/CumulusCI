# Note: Unlike in traditional robot libraries, this docstring will end
# up in output from the libdoc task. For that to happen, it must be
# before the imports.

"""
The following page objects are automatically included when
importing the PageObject library. You should not directly import this
file.

"""

import re
from cumulusci.robotframework.pageobjects import pageobject
from cumulusci.robotframework.pageobjects import BasePage

# This will appear in the generated documentation in place of
# the filename.
TITLE = "Base Page Objects"


@pageobject(page_type="Listing")
class ListingPage(BasePage):
    """Keywords for listing pages"""

    def _go_to_page(self, filter_name=None):
        url_template = "{root}/lightning/o/{object_name}/list"
        url = url_template.format(
            root=self.cumulusci.org.lightning_base_url, object_name=self.object_name
        )
        if filter_name:
            url += "?filterName={}".format(filter_name)
        self.selenium.go_to(url)
        self.salesforce.wait_until_loading_is_complete()

    def _is_current_page(self):
        self.selenium.location_should_contain(
            "/lightning/o/{}/list".format(self.object_name)
        )


@pageobject("Home")
class HomePage(BasePage):
    def _go_to_page(self, filter_name=None):
        url_template = "{root}/lightning/o/{object_name}/home"
        url = url_template.format(
            root=self.cumulusci.org.lightning_base_url, object_name=self.object_name
        )
        self.selenium.go_to(url)
        self.salesforce.wait_until_loading_is_complete()

    def _is_current_page(self):
        self.selenium.location_should_contain(
            "/lightning/o/{}/home".format(self.object_name)
        )


@pageobject("Detail")
class DetailPage(BasePage):
    _page_type = "Detail"

    def _go_to_page(self, object_id=None, **kwargs):
        """Go to the detail page for the given object.

        You may pass in an object id, or you may pass in keyword arguments
        which can be used to look up the object.
        """

        if kwargs and object_id:
            raise Exception("Specify an object id or keyword arguments, but not both")

        if kwargs:
            # note: this will raise an exception if no object is found,
            # or if multiple objects are found.
            object_id = self._get_object(**kwargs)["Id"]

        url_template = "{root}/lightning/r/{object_name}/{object_id}/view"
        url = url_template.format(
            root=self.cumulusci.org.lightning_base_url,
            object_name=self.object_name,
            object_id=object_id,
        )
        self.selenium.go_to(url)
        self.salesforce.wait_until_loading_is_complete()

    def _is_current_page(self, **kwargs):
        """Verify we are on a detail page.

        If keyword arguments are present, this function will go a query
        on the given parameters, assert that the query returns a single
        result, and the verify that the returned object id is part of the url.
        """
        if kwargs:
            # do a lookup to get the object i
            object_id = self._get_object(**kwargs)["Id"]
            pattern = r"/lightning/r/{}/{}/view$".format(self.object_name, object_id)
        else:
            # no kwargs means we should just verify we are on a detail
            # page without regard to which object
            pattern = r"/lightning/r/{}/.*/view$".format(self.object_name)

        location = self.selenium.get_location()
        if not re.search(pattern, location):
            raise Exception(
                "Location '{}' didn't match pattern {}".format(location, pattern)
            )
