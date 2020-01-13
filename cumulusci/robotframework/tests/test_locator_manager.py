import unittest
from unittest import mock
import pytest

from cumulusci.robotframework.locator_manager import (
    register_locators,
    translate_locator,
    LOCATORS,
    locate_element,
)

mock_libs = {}


def mock_get_library_instance(name):
    mock_libs[name] = mock.Mock(name=name)
    return mock_libs[name]


class TestTranslateLocator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        LOCATORS.clear()
        register_locators(
            prefix="test",
            locators={
                "foo": {
                    "message": "{} {}",
                    "bar": {
                        "baz": "//div[@class='baz']",
                        "hello": "//span[text()='Hello, {}']",
                    },
                }
            },
        )

    def test_strip_whitespace_from_locator(self):
        """Verify whitespace is stripped from locator key and args"""
        loc = translate_locator("test", "foo . bar . baz")
        assert loc == "//div[@class='baz']"

    def test_nested_locators(self):
        """Verify dot notation can be used to drill into nested structure"""
        loc = translate_locator("test", "foo.bar.baz")
        assert loc == "//div[@class='baz']"

    def test_arguments(self):
        """Verify arguments appear in the final locator"""
        loc = translate_locator("test", "foo.bar.hello:world")
        assert loc == "//span[text()='Hello, world']"

    def test_multiple_arguments(self):
        """Verify we support more than a single argument"""
        loc = translate_locator("test", "foo.message:hello,world")
        assert loc == "hello world"

    def test_extra_args(self):
        """Verify extra args are ignored

        Maybe we should be throwing an error, but since `.format()`
        doesn't throw an error, we would have to add our own argument
        checking which I think is more trouble than its worth
        """
        loc = translate_locator("test", "foo.message:testing,one,two,three")
        assert loc == "testing one"

    def test_missing_args(self):
        """Verify a friendly exception is thrown for missing arguments"""
        expected_error = "Not enough arguments were supplied"
        with pytest.raises(Exception, match=expected_error):
            translate_locator("test", "foo.bar.hello")

    def test_bad_locator(self):
        """Verify a locator that resolves to a non-string raises an error"""
        expected_error = "Expected locator to be of type string, but was <class 'dict'>"
        with pytest.raises(TypeError, match=expected_error):
            translate_locator("test", "foo.bar")

    def test_unknown_locator(self):
        """Verify that an invalid locator path throws a useful error

        Not only that, but verify that what appears in the error is
        the first part of the locator key that wasn't found.
        """
        expected_error = "locator test:foo.not not found"
        with pytest.raises(KeyError, match=expected_error):
            translate_locator("test", "foo.not.valid")


class TestLocateElement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        LOCATORS.clear()
        register_locators(
            prefix="test",
            locators={"foo": {"bar": {"hello": "//span[text()='Hello, {}']"}}},
        )

    def test_locate_element(self):
        """Verify that the locate_element function translates the
        locator and calls SeleniumLibrary.get_webelement with the
        translated locator
        """

        locator = "foo.bar.hello:world"
        parent = mock.Mock()
        tag = ""
        constraints = {}

        with mock.patch(
            "robot.libraries.BuiltIn.BuiltIn.get_library_instance",
            side_effect=mock_get_library_instance,
        ):
            locate_element("test", parent, locator, tag, constraints)
            mock_libs["SeleniumLibrary"].get_webelement.assert_called_with(
                "//span[text()='Hello, world']"
            )


class TestRegisterLocators(unittest.TestCase):
    def setUp(self):
        LOCATORS.clear()

    def test_register_locators(self):
        """Verify that register_locators updates the LOCATORS dictionary"""
        register_locators("test", {"foo": "//div/foo"})

        expected = {"test": {"foo": "//div/foo"}}
        self.assertDictEqual(LOCATORS, expected)

    def test_multiple_registrations(self):
        """Verify that more than one prefix can be registered"""

        register_locators("test1", {"foo": "//div/foo"})
        register_locators("test2", {"bar": "//div/bar"})

        expected = {"test1": {"foo": "//div/foo"}, "test2": {"bar": "//div/bar"}}
        self.assertDictEqual(LOCATORS, expected)

    def test_register_locators_merge(self):
        """Verify that calling register_locators will merge the new locators
        with existing locators for a given prefix, rather than
        replacing them.
        """
        register_locators("test1", {"foo": {"one": "//div/one"}})
        register_locators("test1", {"foo": {"two": "//div/two"}})

        expected = {"test1": {"foo": {"one": "//div/one", "two": "//div/two"}}}
        self.assertDictEqual(LOCATORS, expected)
