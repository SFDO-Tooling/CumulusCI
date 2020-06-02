"""Tests for the PageObjects class

Testing notes:

The PageObjects library uses robot's BuiltIn library. However,
instantiating that will throw an error if done outside the context of
a running robot test. To work around that, these tests mock out the
_get_context method to fool the BuiltIn library into not complaining.

These tests use two external files in the same directory as this test:
FooTestPage.py and BarTestPage.py. FooTestPage has a single keyword,
BarTestPage has two.

"""

import unittest
import os.path
from unittest import mock
from cumulusci.robotframework import PageObjects
from cumulusci.robotframework.CumulusCI import CumulusCI
from cumulusci.robotframework.pageobjects.PageObjectLibrary import _PageObjectLibrary
from cumulusci.robotframework.pageobjects import (
    BasePage,
    ListingPage,
    EditModal,
    NewModal,
    HomePage,
    DetailPage,
)
from robot.libraries.BuiltIn import BuiltIn
import robot.utils


HERE = os.path.dirname(__file__)
FOO_PATH = os.path.join(HERE, "FooTestPage.py")
BAR_PATH = os.path.join(HERE, "BarTestPage.py")
CORE_KEYWORDS = [
    "current_page_should_be",
    "get_page_object",
    "go_to_page",
    "load_page_object",
    "log_page_object_keywords",
    "wait_for_modal",
    "wait_for_page_object",
]

BASE_REGISTRY = {
    ("Detail", ""): DetailPage,
    ("Edit", ""): EditModal,
    ("Home", ""): HomePage,
    ("Listing", ""): ListingPage,
    ("New", ""): NewModal,
}

# this is the importer used by the page objects, which makes it easy
# peasy to import by file path
importer = robot.utils.Importer()


class MockGetLibraryInstance:
    libs = {
        "SeleniumLibrary": mock.Mock(),
        "cumulusci.robotframework.CumulusCI": CumulusCI(),
        "cumulusci.robotframework.Salesforce": mock.Mock(),
    }

    def __call__(self, libname):
        if libname in self.libs:
            return self.libs[libname]
        else:
            raise Exception("unknown library: {}".format(libname))


@mock.patch(
    "robot.libraries.BuiltIn.BuiltIn.get_library_instance",
    side_effect=MockGetLibraryInstance(),
)
# We have to mock out _get_context or the robot libraries will
# throw an exception saying it cannot access the execution context.
@mock.patch("robot.libraries.BuiltIn.BuiltIn._get_context")
class TestPageObjects(unittest.TestCase):
    def test_PageObject(self, get_context_mock, get_library_instance_mock):
        """Smoke test to make sure the default registry is set up and keywords exist"""
        po = PageObjects()
        self.assertEqual(po.get_keyword_names(), CORE_KEYWORDS)
        self.assertEqual(po.registry, BASE_REGISTRY)

    def test_PageObject_registry_with_custom_pageobjects(
        self, get_context_mock, get_library_instance_mock
    ):
        """Verify that custom page objects get added to the registry"""
        po = PageObjects(FOO_PATH, BAR_PATH)

        # The page object class will have been imported by robot.utils.Importer,
        # so we need to use that here to validate which class got imported.
        FooTestPage = importer.import_class_or_module_by_path(FOO_PATH)
        BarTestPage = importer.import_class_or_module_by_path(BAR_PATH)

        expected_registry = BASE_REGISTRY
        expected_registry.update(
            {("Test", "Foo__c"): FooTestPage, ("Test", "Bar__c"): BarTestPage}
        )

        self.assertEqual(po.registry, expected_registry)

    def test_namespaced_object_name(self, get_context_mock, get_library_instance_mock):
        """Verify that the object name is prefixed by the namespace when there's a namespace"""
        with mock.patch.object(
            CumulusCI, "get_namespace_prefix", return_value="foobar__"
        ):
            po = PageObjects(FOO_PATH)

            FooTestPage = importer.import_class_or_module_by_path(FOO_PATH)
            MockGetLibraryInstance.libs["FooTestPage"] = _PageObjectLibrary(
                FooTestPage()
            )

            pobj = po.get_page_object("Test", "Foo__c")
            self.assertEqual(pobj.object_name, "foobar__Foo__c")

    def test_non_namespaced_object_name(
        self, get_context_mock, get_library_instance_mock
    ):
        """Verify that the object name is not prefixed by a namespace when there is no namespace"""
        with mock.patch.object(CumulusCI, "get_namespace_prefix", return_value=""):
            po = PageObjects(FOO_PATH)

            FooTestPage = importer.import_class_or_module_by_path(FOO_PATH)
            MockGetLibraryInstance.libs["FooTestPage"] = _PageObjectLibrary(
                FooTestPage()
            )

            pobj = po.get_page_object("Test", "Foo__c")
            self.assertEqual(pobj.object_name, "Foo__c")


@mock.patch(
    "robot.libraries.BuiltIn.BuiltIn.get_library_instance",
    side_effect=MockGetLibraryInstance(),
)
class TestBasePage(unittest.TestCase):
    """Some low-level tests of page object classes"""

    def test_no_implicit_wait(self, mock_get_library_instance):
        """Verify the "implicit wait" context manager restores the value"""

        selib = BuiltIn().get_library_instance("SeleniumLibrary")
        selib.set_selenium_implicit_wait.return_value = 7
        selib.set_selenium_implicit_wait.reset_mock()

        page = BasePage()
        with page._no_implicit_wait():
            pass

        # The first call should pass in zero to turn off the
        # implicit wait.  We've configured the mocked function to
        # return '7'. The second call should pass the return value
        # of the first call
        selib.set_selenium_implicit_wait.assert_has_calls(
            (mock.call(0), mock.call(7)), any_order=False
        )

    def test_no_implicit_wait_with_exception(self, mock_get_library_instance):
        """Verify the "implicit wait" context manager restores the value even if exception occurs"""

        selib = BuiltIn().get_library_instance("SeleniumLibrary")
        selib.set_selenium_implicit_wait.return_value = 42
        selib.set_selenium_implicit_wait.reset_mock()

        page = BasePage()
        try:
            with page._no_implicit_wait():
                raise Exception("Danger Will Robinson!")
        except Exception:
            pass

        # The first call should pass in zero to turn off the
        # implicit wait.  We've configured the mocked function to
        # return '42'. The second call should pass the return value
        # of the first call
        selib.set_selenium_implicit_wait.assert_has_calls(
            (mock.call(0), mock.call(42)), any_order=False
        )
