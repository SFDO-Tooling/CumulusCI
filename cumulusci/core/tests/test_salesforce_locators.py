import unittest
from robot.libraries.BuiltIn import RobotNotRunningError
from cumulusci.robotframework.Salesforce import Salesforce
from unittest import mock
from pathlib import Path


# FIXME: we shouldn't have to tweak these tests for every
# version. The tests should be smarter.
class TestLocators(unittest.TestCase):
    @mock.patch("cumulusci.robotframework.Salesforce.Salesforce.get_latest_api_version")
    def test_locators_in_robot_context(self, get_latest_api_version):
        """Verify we can get locators for the current org api version"""
        get_latest_api_version.return_value = 50.0

        # This instantiates the robot library, mimicking a robot library import.
        # We've mocked out the code that would otherwise throw an error since
        # we're not running in the context of a robot test. The library should
        # return the latest version of the locators.
        sf = Salesforce()

        expected = "cumulusci.robotframework.locators_50"
        actual = sf.locators_module.__name__
        message = "expected to load '{}', actually loaded '{}'".format(expected, actual)
        self.assertEqual(expected, actual, message)

        pass

    @mock.patch(
        "robot.libraries.BuiltIn.BuiltIn.get_library_instance",
        side_effect=RobotNotRunningError(),
    )
    def test_locators_outside_robot_context(self, builtin_mock):
        """Verify that we get the latest locators if not running in the context of a robot test"""

        # This instantiates the robot library, mimicing a robot library import
        # however, because we've mocked get_library_instance to throw an error,
        # we expect the library to still be instantiated, but with the latest
        # version of the locators.

        sf = Salesforce()

        locator_folder = Path("./cumulusci/robotframework")
        locator_modules = sorted(locator_folder.glob("locators_[0-9][0-9].py"))
        expected = f"cumulusci.robotframework.{locator_modules[-1].stem}"

        actual = sf.locators_module.__name__
        message = "expected to load '{}', actually loaded '{}'".format(expected, actual)
        self.assertEqual(expected, actual, message)

    def test_locators_51(self):
        """Verify that locators_51 is a superset of the locators_50

        This test is far from perfect, but it should at least flag a
        catastrophic error in how locators for a version that augments
        the locators from previous versions.

        Note: this test assumes that locators_51 doesn't delete any of the
        keys from 50.

        """
        import cumulusci.robotframework.locators_50 as locators_50
        import cumulusci.robotframework.locators_51 as locators_51

        keys_50 = set(locators_50.lex_locators)
        keys_51 = set(locators_51.lex_locators)

        self.assertNotEqual(
            id(locators_50.lex_locators),
            id(locators_51.lex_locators),
            "locators_50.lex_locators and locators_51.lex_locators are the same object",
        )
        self.assertTrue(len(keys_50) > 0)
        self.assertTrue(keys_50.issubset(keys_51))
