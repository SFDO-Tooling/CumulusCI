from robot.libraries.BuiltIn import BuiltIn
import re


class BasePage(object):
    _object_name = None

    def __init__(self, object_name=None):
        if object_name:
            self._object_name = object_name

    @property
    def object_name(self):
        object_name = self._object_name

        # the length check is to skip objects from a different namespace
        # like foobar__otherpackageobject__c
        if object_name is not None:
            parts = object_name.split("__")
            if len(parts) == 2 and parts[-1] == "c":
                # get_namespace_prefix already takes care of returning an actual
                # prefix or an empty string depending on whether the package is managed
                object_name = "{}{}".format(
                    self.cumulusci.get_namespace_prefix(), object_name
                )
        return object_name

    @property
    def builtin(self):
        """Returns an instance of robot framework's BuiltIn library"""
        return BuiltIn()

    @property
    def cumulusci(self):
        """Returns the instance of the imported CumulusCI library"""
        return self.builtin.get_library_instance("cumulusci.robotframework.CumulusCI")

    @property
    def salesforce(self):
        """Returns the instance of the imported Salesforce library"""
        return self.builtin.get_library_instance("cumulusci.robotframework.Salesforce")

    @property
    def selenium(self):
        """Returns the instance of the imported SeleniumLibrary library"""
        return self.builtin.get_library_instance("SeleniumLibrary")

    def _get_object(self, **kwargs):
        """Get the object associated with the given keyword arguments.

        This performs a salesforce query. It will raise an exception unless
        exactly one result is returned from the query.
        """
        results = self.salesforce.salesforce_query(self.object_name, **kwargs)
        if len(results) == 0:
            human_friendly_args = ", ".join(
                ["{}={}".format(key, kwargs[key]) for key in kwargs]
            )
            raise Exception(
                "no {} matches {}".format(self.object_name, human_friendly_args)
            )
        elif len(results) > 1:
            raise Exception("Query returned {} objects".format(len(results)))
        else:
            return results[0]


class ListingPage(BasePage):
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


class DetailPage(BasePage):
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
