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

import os.path
import sys
from contextlib import contextmanager
from unittest import mock

import pytest
import robot.utils
from robot.libraries.BuiltIn import BuiltIn

from cumulusci.robotframework import PageObjects
from cumulusci.robotframework.CumulusCI import CumulusCI
from cumulusci.robotframework.pageobjects.BasePageObjects import (
    DetailPage,
    HomePage,
    ListingPage,
)
from cumulusci.robotframework.pageobjects.PageObjectLibrary import _PageObjectLibrary
from cumulusci.utils import temporary_dir

HERE = os.path.dirname(__file__)
FOO_PATH = os.path.join(HERE, "FooTestPage.py")
CUSTOM_PATH = os.path.join(HERE, "CustomObjectTestPage.py")

# this is the importer used by the page objects, which makes it easy
# peasy to import by file path
importer = robot.utils.Importer()

# These tests don't need an org, so mocking it out will prevent some
# keywords from trying to create the org.
cci_lib = CumulusCI()
cci_lib._org = mock.Mock()


class MockGetLibraryInstance:
    """Mock robot's get_library_instance method

    This will return instances of the libraries used in this set of tests.
    """

    libs = {
        "SeleniumLibrary": mock.Mock(),
        "cumulusci.robotframework.CumulusCI": cci_lib,
        "cumulusci.robotframework.Salesforce": mock.Mock(),
        "cumulusci.robotframework.SalesforceAPI": mock.Mock(),
        # Note: the fact that we're using "Contact" here is largely
        # irrelevant. The important thing is that we create a page
        # object for the base types of Home, Listing,and Detail
        "ContactHomePage": _PageObjectLibrary(HomePage("Contact")),
        "ContactListingPage": _PageObjectLibrary(ListingPage("Contact")),
        "ContactDetailPage": _PageObjectLibrary(DetailPage("Contact")),
    }

    def __call__(self, libname):
        if libname in self.libs:
            return self.libs[libname]
        else:
            raise Exception("unknown library: {}".format(libname))


@contextmanager
def reload_PageObjects(*args):
    # Reset the registry and re-import the built-in page objects
    saved_registry = PageObjects.registry
    PageObjects._reset()
    import cumulusci.robotframework.pageobjects.BasePageObjects  # noqa: F401
    import cumulusci.robotframework.pageobjects.ObjectManagerPageObject  # noqa: F401

    yield PageObjects(*args)

    PageObjects._reset()
    PageObjects.registry = saved_registry


@mock.patch(
    "robot.libraries.BuiltIn.BuiltIn.get_library_instance",
    side_effect=MockGetLibraryInstance(),
)
# We have to mock out _get_context or the robot libraries will
# throw an exception saying it cannot access the execution context.
@mock.patch("robot.libraries.BuiltIn.BuiltIn._get_context")
class TestPageObjects:
    def test_PageObject(self, get_context_mock, get_library_instance_mock):
        """Smoke test to make sure the default registry is set up and keywords exist"""

        with reload_PageObjects() as po:
            expected_keywords = [
                "current_page_should_be",
                "get_page_object",
                "go_to_page",
                "load_page_object",
                "log_page_object_keywords",
                "wait_for_modal",
                "wait_for_page_object",
            ]
            actual_keywords = po.get_keyword_names()
            assert actual_keywords == expected_keywords

            # fmt: off
            # This is much easier to read than if black were to reformat it.
            expected_registry = {
                ("Detail", ""): "<class 'cumulusci.robotframework.pageobjects.BasePageObjects.DetailPage'>",
                ("Edit", ""): "<class 'cumulusci.robotframework.pageobjects.BasePageObjects.EditModal'>",
                ("Home", ""): "<class 'cumulusci.robotframework.pageobjects.BasePageObjects.HomePage'>",
                ("Listing", ""): "<class 'cumulusci.robotframework.pageobjects.BasePageObjects.ListingPage'>",
                ("New", ""): "<class 'cumulusci.robotframework.pageobjects.BasePageObjects.NewModal'>",
                ("ObjectManager", ""): "<class 'cumulusci.robotframework.pageobjects.ObjectManagerPageObject.ObjectManagerPage'>",
            }
            # fmt: on
            actual_registry = {key: repr(value) for key, value in po.registry.items()}
            assert actual_registry == expected_registry

    def test_file_in_pythonpath(self, get_context_mock, get_library_instance_mock):
        """Verify we can find a page object via PYTHONPATH"""
        # PageObjects will throw an error if it can't find the file.
        # As long as this doesn't throw an error, we're golden.
        sys_path = sys.path.copy()
        if HERE not in sys.path:
            sys_path.append(HERE)
        with mock.patch.object(sys, "path", sys_path):
            PageObjects("FooTestPage.py")

    def test_exception_not_found(self, get_context_mock, get_library_instance_mock):
        """Verify we get an assertion of we can't find a page object file"""
        with pytest.raises(
            ImportError, match="Unable to find page object file 'bogus.py'"
        ):
            PageObjects("bogus.py")

    def test_import_failed(self, get_context_mock, get_library_instance_mock):
        with temporary_dir() as d:
            with open("busted.py", "w") as f:
                f.write("class Busted  # incomplete class\n")
                f.close()
                with mock.patch.object(sys, "path", sys.path + [d]):
                    with pytest.raises(
                        ImportError,
                        match="Unable to import page object 'busted.py': .*",
                    ):
                        PageObjects("busted.py")

    def test_PageObject_registry_with_custom_pageobjects(
        self, get_context_mock, get_library_instance_mock
    ):
        """Verify that custom page objects get added to the registry"""
        with reload_PageObjects(FOO_PATH, CUSTOM_PATH) as po:
            # fmt: off
            # This is much easier to read than if black were to reformat it.
            expected_registry = {
                ("Detail", ""): "<class 'cumulusci.robotframework.pageobjects.BasePageObjects.DetailPage'>",
                ("Edit", ""): "<class 'cumulusci.robotframework.pageobjects.BasePageObjects.EditModal'>",
                ("Home", ""): "<class 'cumulusci.robotframework.pageobjects.BasePageObjects.HomePage'>",
                ("Listing", ""): "<class 'cumulusci.robotframework.pageobjects.BasePageObjects.ListingPage'>",
                ("New", ""): "<class 'cumulusci.robotframework.pageobjects.BasePageObjects.NewModal'>",
                ("ObjectManager", ""): "<class 'cumulusci.robotframework.pageobjects.ObjectManagerPageObject.ObjectManagerPage'>",
                # the custom page object uses an alias for the object name so it will be in the registry twice
                ("Listing", "CustomObject__c"): "<class 'CustomObjectTestPage.CustomObjectListingPage'>",
                ("Listing", "Custom Object"): "<class 'CustomObjectTestPage.CustomObjectListingPage'>",
                ("Test", "Foo__c"): "<class 'FooTestPage.FooTestPage'>",
            }
            # fmt: on
            actual_registry = {key: repr(value) for key, value in po.registry.items()}
            assert actual_registry == expected_registry

    def test_namespaced_object_name(self, get_context_mock, get_library_instance_mock):
        """Verify that the object name is prefixed by the namespace when there's a namespace"""
        with mock.patch.object(
            CumulusCI, "get_namespace_prefix", return_value="foobar__"
        ):
            with reload_PageObjects(FOO_PATH) as po:

                FooTestPage = importer.import_class_or_module_by_path(FOO_PATH)
                MockGetLibraryInstance.libs["FooTestPage"] = _PageObjectLibrary(
                    FooTestPage()
                )

                pobj = po.get_page_object("Test", "Foo__c")
                assert pobj.object_name == "foobar__Foo__c"

    def test_non_namespaced_object_name(
        self, get_context_mock, get_library_instance_mock
    ):
        """Verify that the object name is not prefixed by a namespace when there is no namespace"""
        with mock.patch.object(CumulusCI, "get_namespace_prefix", return_value=""):
            with reload_PageObjects(FOO_PATH) as po:

                FooTestPage = importer.import_class_or_module_by_path(FOO_PATH)
                MockGetLibraryInstance.libs["FooTestPage"] = _PageObjectLibrary(
                    FooTestPage()
                )

                pobj = po.get_page_object("Test", "Foo__c")
                assert pobj.object_name == "Foo__c"

    def test_go_to_page_with_locator(self, get_context_mock, get_library_instance_mock):
        """Verify 'Go to page' accepts and uses a locator argument

        See W-8580487 for more details
        """

        with reload_PageObjects() as po:
            for page_type in ("Home", "Listing", "Detail"):
                # the exact locator isn't important for the test, we
                # just need to make sure it is passed on to
                # wait_until_loading_is_complete
                locator = f"//div[@class='{page_type}']"
                po.go_to_page(page_type, "Contact", locator=locator)
                sflib = BuiltIn().get_library_instance(
                    "cumulusci.robotframework.Salesforce"
                )
                sflib.wait_until_loading_is_complete.assert_called_with(locator=locator)

    def test_go_to_page_without_locator(
        self, get_context_mock, get_library_instance_mock
    ):
        """Verify 'Go to page' doesn't require a locator"""

        with reload_PageObjects() as po:
            for page_type in ("Home", "Listing", "Detail"):
                po.go_to_page(page_type, "Contact")
                sflib = BuiltIn().get_library_instance(
                    "cumulusci.robotframework.Salesforce"
                )
                sflib.wait_until_loading_is_complete.assert_called_with(locator=None)


@mock.patch(
    "robot.libraries.BuiltIn.BuiltIn.get_library_instance",
    side_effect=MockGetLibraryInstance(),
)
class TestBasePage:
    """Some low-level tests of page object classes"""

    def test_no_implicit_wait(self, mock_get_library_instance):
        """Verify the "implicit wait" context manager restores the value"""

        selib = BuiltIn().get_library_instance("SeleniumLibrary")
        selib.set_selenium_implicit_wait.return_value = 7
        selib.set_selenium_implicit_wait.reset_mock()

        from cumulusci.robotframework.pageobjects import BasePage

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

        from cumulusci.robotframework.pageobjects import BasePage

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
