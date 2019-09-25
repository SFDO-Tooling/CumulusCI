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
from cumulusci.robotframework.pageobjects.PageObjectLibrary import _PageObjectLibrary


HERE = os.path.dirname(__file__)
FOO_PATH = os.path.join(HERE, "FooTestPage.py")
BAR_PATH = os.path.join(HERE, "BarTestPage.py")
CORE_KEYWORDS = [
    "current_page_should_be",
    "get_page_object",
    "go_to_page",
    "load_page_object",
    "log_page_object_keywords",
]


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
        po = PageObjects()
        self.assertEqual(po.get_keyword_names(), CORE_KEYWORDS)
        self.assertEqual(po.registry, {})

        po = PageObjects(FOO_PATH, BAR_PATH)
        if hasattr(self, "assertCountEqual"):
            self.assertCountEqual(
                po.registry.keys(), (("Test", "Foo__c"), ("Test", "Bar__c"))
            )
        else:
            # gah! python3 renamed this assert
            self.assertItemsEqual(
                po.registry.keys(), (("Test", "Foo__c"), ("Test", "Bar__c"))
            )

        # This is done here rather than at the top of this file
        # since doing it at the module level would register
        # the keywords before we're ready for them to be registered.
        from .FooTestPage import FooTestPage
        from .BarTestPage import BarTestPage

        self.assertEquals(po.registry[("Test", "Foo__c")], FooTestPage)
        self.assertEquals(po.registry[("Test", "Bar__c")], BarTestPage)

    def test_library_wrapper(self, get_context_mock, get_library_instance_mock):
        """Verify the library wrapper properly wraps an instance of a class

        When we load a page object, we wrap it in a lightweight wrapper
        which implements robot's hybrid library api (read: it has a
        get_keyword_names method). This verifies that the wrapper exposes
        all of the methods as keywords.
        """
        from .BarTestPage import BarTestPage

        pobj = _PageObjectLibrary(BarTestPage())
        self.assertEquals(
            pobj.get_keyword_names(),
            ["bar_keyword_1", "bar_keyword_2", "log_current_page_object"],
        )
        self.assertEquals(pobj._libname, "BarTestPage")

    def test_library_wrapper_keywords(
        self, get_context_mock, get_library_instance_mock
    ):
        """Verify that the keywords of a page object are callable"""

        from .BarTestPage import BarTestPage

        pobj = _PageObjectLibrary(BarTestPage())

        # verify we can call the keywords
        self.assertEquals(pobj.bar_keyword_1("hello"), "bar keyword 1: hello")
        self.assertEquals(pobj.bar_keyword_2("world"), "bar keyword 2: world")

    def test_get_pageobject(self, get_context_mock, get_library_instance_mock):
        """Verify we can get a reference to a page object"""
        po = PageObjects(FOO_PATH, BAR_PATH)

        # make sure the mock knows about FooTestPage
        from .FooTestPage import FooTestPage

        MockGetLibraryInstance.libs["FooTestPage"] = _PageObjectLibrary(FooTestPage())

        pobj = po.get_page_object("Test", "Foo__c")
        self.assertIsInstance(pobj, _PageObjectLibrary)
        self.assertEquals(pobj._libname, "FooTestPage")

    @mock.patch("robot.api.logger.info")
    def test_log_page_object_keywords(
        self, log_mock, get_context_mock, get_library_instance_mock
    ):
        """Verify that the log_page_objects keyword logs keywords from all imported page objects"""
        po = PageObjects(FOO_PATH, BAR_PATH)
        po.log_page_object_keywords()
        # In addition to the hard-coded keywords, each page object
        # should also have keywords that it inherited from the base
        # class.
        expected_calls = [
            mock.call(
                "('Test', 'Bar__c'): bar_keyword_1, bar_keyword_2, log_current_page_object"
            ),
            mock.call("('Test', 'Foo__c'): foo_keyword_1, log_current_page_object"),
        ]
        log_mock.assert_has_calls(expected_calls, any_order=True)

    def test_namespaced_object_name(self, get_context_mock, get_library_instance_mock):
        """Verify that the object name is prefixed by the namespace when there's a namespace"""
        with mock.patch.object(
            CumulusCI, "get_namespace_prefix", return_value="foobar__"
        ):
            po = PageObjects(FOO_PATH)

            # make sure the mock knows about FooTestPage
            from .FooTestPage import FooTestPage

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

            # make sure the mock knows about FooTestPage
            from .FooTestPage import FooTestPage

            MockGetLibraryInstance.libs["FooTestPage"] = _PageObjectLibrary(
                FooTestPage()
            )

            pobj = po.get_page_object("Test", "Foo__c")
            self.assertEqual(pobj.object_name, "Foo__c")
