from pathlib import Path
from unittest import mock

from robot.libraries.BuiltIn import RobotNotRunningError

from cumulusci.robotframework.Salesforce import Salesforce


# FIXME: we shouldn't have to tweak these tests for every
# version. The tests should be smarter.
class TestLocators:
    @mock.patch(
        "cumulusci.robotframework.SalesforceAPI.SalesforceAPI.get_latest_api_version"
    )
    def test_locators_in_robot_context(self, get_latest_api_version):
        """Verify we can get locators for the current org api version"""
        get_latest_api_version.return_value = 56.0

        # This instantiates the robot library, mimicking a robot library import.
        # We've mocked out the code that would otherwise throw an error since
        # we're not running in the context of a robot test. The library should
        # return the latest version of the locators.
        sf = Salesforce()

        expected = "cumulusci.robotframework.locators_56"
        actual = sf.locators_module.__name__
        message = "expected to load '{}', actually loaded '{}'".format(expected, actual)
        assert expected == actual, message

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
        assert expected == actual, message

    def test_locators_56(self):
        """Verify that locators_56 is a superset of the locators_54

        This test is far from perfect, but it should at least flag a
        catastrophic error in how locators for a version that augments
        the locators from previous versions.

        Note: this test assumes that locators_56 doesn't delete any of the
        keys from 54.

        """
        import cumulusci.robotframework.locators_54 as locators_54
        import cumulusci.robotframework.locators_56 as locators_56

        keys_54 = set(locators_54.lex_locators)
        keys_56 = set(locators_56.lex_locators)

        assert id(locators_54.lex_locators) != id(
            locators_56.lex_locators
        ), "locators_54.lex_locators and locators_56.lex_locators are the same object"
        assert len(keys_54) > 0
        assert keys_56.issubset(keys_54)
