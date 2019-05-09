from robot.libraries.BuiltIn import BuiltIn
import re


class BasePage(object):
    def __init__(self, object_name=None):
        if object_name:
            self.object_name = object_name

    def some_keyword(self):
        BuiltIn().log("some keyword; object name is {}".format(self.object_name))

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


class ListingPage(BasePage):
    # This needs to be defined by a subclass, or passed in to
    # the constructor
    object_name = None

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
    def _is_current_page(self, **kwargs):
        """Verify we are on a detail page.

        If keyword arguments are present, this function will go a query
        on the given parameters, assert that the query returns a single
        result, and the verify that the returned object id is part of the url.
        """
        if kwargs:
            # if we have kwargs, we need to query for that object, assert
            # that we got back exactly one result, and then make sure that
            # object id is part of the url
            results = self.salesforce.salesforce_query(self.object_name, **kwargs)
            if len(results) == 0:
                raise Exception(
                    "no {} matches {}".format(self.object_name, str(kwargs))
                )
            elif len(results) > 1:
                raise Exception("Query returned {} objects".format(len(results)))
            else:
                pattern = r"/lightning/r/{}/{}/view$".format(
                    self.object_name, results[0]["Id"]
                )
        else:
            # no kwargs means we should just verify we are on a detail
            # page without regard to which object
            pattern = r"/lightning/r/{}/.*/view$".format(self.object_name)

        location = self.selenium.get_location()
        self.builtin.log_to_console("\npattern: {}".format(pattern))
        if not re.search(pattern, location):
            raise Exception(
                "Location '{}' didn't match pattern {}".format(location, pattern)
            )
