from cumulusci.robotframework.pageobjects import PageObject

"""
This contains base classes for objects of type standard_objectPage
"""


class ObjectHomePage(PageObject):
    PAGE_TYPE = "objectPage"
    OBJECT_API_NAME = None

    def _is_current_page(self):
        page_url = self.selenium.get_location()
        return "/lightning/o/{}/home".format(self.OBJECT_API_NAME) in page_url


class ObjectListPage(PageObject):
    PAGE_TYPE = "objectPage"
    OBJECT_API_NAME = None

    def _is_current_page(self):
        page_url = self.selenium.get_location()
        return "/lightning/o/{}/list".format(self.OBJECT_API_NAME) in page_url


class ObjectNewPage(PageObject):
    PAGE_TYPE = "objectPage"
    OBJECT_API_NAME = None

    def _is_current_page(self):
        page_url = self.selenium.get_location()
        return "/lightning/o/{}/new".format(self.OBJECT_API_NAME) in page_url
