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
import mock
from cumulusci.robotframework import PageObjects
from cumulusci.robotframework.CumulusCI import CumulusCI

HERE = os.path.dirname(__file__)
FOO_PATH = os.path.join(HERE, "FooTestPage.py")
BAR_PATH = os.path.join(HERE, "BarTestPage.py")
CORE_KEYWORDS = [
    "current_page_should_be",
    "go_to_page",
    "load_page_object",
    "log_page_object_keywords",
]


def mock_builtin_get_library_instance(libname):
    if libname == "cumulusci.robotframework.CumulusCI":
        return CumulusCI()
    return mock.Mock()


@mock.patch(
    "robot.libraries.BuiltIn.BuiltIn.get_library_instance",
    side_effect=mock_builtin_get_library_instance,
)
# We have to mock out _get_context or the robot libraries will
# throw an exception saying it cannot access the execution context.
@mock.patch("robot.libraries.BuiltIn.BuiltIn._get_context")
class TestPageObjects(unittest.TestCase):
    def test_PageObject(self, get_context_mock, get_library_instance_mock):
        po = PageObjects()
        # no page objects loaded, so get_keyword_names should only return
        # the core keywords
        self.assertEqual(po.get_keyword_names(), CORE_KEYWORDS)
        self.assertEqual(po.registry, {})

    def test_load_single_page_object(self, get_context_mock, get_library_instance_mock):
        """Verify that we don't see page object keywords until they are explicitly requested"""

        po = PageObjects(FOO_PATH)

        # Until we request the page object, we shouldn't be able to
        # see the page-specific keywords
        self.assertEqual(po.get_keyword_names(), CORE_KEYWORDS)

        # Now load the page object and verify the Foo keyword shows up
        po.load_page_object("Test", "Foo")
        self.assertEqual(po.get_keyword_names(), CORE_KEYWORDS + ["foo_keyword_1"])

    def test_page_object_keyword_is_callable(
        self, get_context_mock, get_library_instance_mock
    ):
        """Assert that the page object keyword is callable"""
        po = PageObjects(FOO_PATH)
        po.load_page_object("Test", "Foo")
        result = po.foo_keyword_1("hello")
        self.assertEqual(result, "foo keyword 1: hello")

    def test_load_multiple_page_objects(
        self, get_context_mock, get_library_instance_mock
    ):
        """Verify that we can import multiple page objects, but only one is visible at a time

        This test is based on the current design of only allowing a
        single page object to be active at a time. That might change
        in the future - we might end up having page objects be pushed
        on a stack.

        """
        po = PageObjects(FOO_PATH, BAR_PATH)

        # Until we request the page object, we shouldn't be able to
        # see any keywords except the core page object keywords
        self.assertEqual(po.get_keyword_names(), CORE_KEYWORDS)

        # now load the "Foo" page object and verify only the Foo keyword
        # shows up and is callable.
        po.load_page_object("Test", "Foo")
        self.assertEqual(po.get_keyword_names(), CORE_KEYWORDS + ["foo_keyword_1"])
        self.assertEqual(po.foo_keyword_1("hello"), "foo keyword 1: hello")

        # now load the "Bar" page object and verify only the Bar keyword
        # shows up and is callable.
        po.load_page_object("Test", "Bar")
        self.assertEqual(
            po.get_keyword_names(), CORE_KEYWORDS + ["bar_keyword_1", "bar_keyword_2"]
        )
        self.assertEqual(po.bar_keyword_1("hello"), "bar keyword 1: hello")

    @mock.patch("robot.api.logger.info")
    def test_log_page_object_keywords(
        self, log_mock, get_context_mock, get_library_instance_mock
    ):
        """Verify that the log_page_objects keyword logs keywords from all imported page objects"""
        po = PageObjects(FOO_PATH, BAR_PATH)
        po.log_page_object_keywords()
        expected_calls = [
            mock.call("('Test', 'Foo'): foo_keyword_1"),
            mock.call("('Test', 'Bar'): bar_keyword_1, bar_keyword_2"),
        ]
        log_mock.assert_has_calls(expected_calls, any_order=True)

    def test_namespaced_object_name(self, get_context_mock, get_library_instance_mock):
        """Verify that the object name is prefixed by the namespace when there's a namespace"""
        with mock.patch.object(
            CumulusCI, "get_namespace_prefix", return_value="foobar__"
        ):
            pobj = PageObjects().load_page_object("Listing", "CustomObject__c")
            self.assertEqual(pobj.object_name, "foobar__CustomObject__c")

    def test_non_namespaced_object_name(
        self, get_context_mock, get_library_instance_mock
    ):
        """Verify that the object name is not prefixed by a namespace when there is no namespace"""
        with mock.patch.object(CumulusCI, "get_namespace_prefix", return_value=""):
            pobj = PageObjects().load_page_object("Listing", "CustomObject__c")
            self.assertEqual(pobj.object_name, "CustomObject__c")
