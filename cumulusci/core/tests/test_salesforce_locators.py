import unittest
from robot.libraries.BuiltIn import RobotNotRunningError
from cumulusci.robotframework.Salesforce import Salesforce
import mock


class TestLocators(unittest.TestCase):
    @mock.patch("cumulusci.robotframework.Salesforce.Salesforce.cumulusci")
    def test_locators_in_robot_context(self, cumulusci_mock):
        """Verify we can get locators for the current org api version"""
        cumulusci_mock.tooling._call_salesforce.return_value.json.return_value = [
            {"version": "45.0"}
        ]

        # This instantiates the robot library, mimicing a robot library import.
        # We've mocked out the code that would otherwise throw an error since
        # we're not running in the context of a robot test. The library should
        # return the latest version of the locators.
        sf = Salesforce()

        expected = "cumulusci.robotframework.locators_45"
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
        expected = "cumulusci.robotframework.locators_46"
        actual = sf.locators_module.__name__
        message = "expected to load '{}', actually loaded '{}'".format(expected, actual)
        self.assertEqual(expected, actual, message)

    def test_locators_46(self):
        """Verify that locators_46 is a superset of the locators_45

        This test is far from perfect, but it should at least flag a
        catastrophic error in how locators for a version augment the
        locators for previous versions.

        Note: this test assumes that locators_46 doesn't delete any of the
        keys from 45.

        """
        import cumulusci.robotframework.locators_45 as locators_45
        import cumulusci.robotframework.locators_46 as locators_46

        keys_45 = set(locators_45.lex_locators)
        keys_46 = set(locators_46.lex_locators)

        self.assertNotEqual(
            id(locators_45.lex_locators),
            id(locators_46.lex_locators),
            "locators_45.lex_locators and locators_46.lex_locators are the same object",
        )
        self.assertTrue(len(keys_45) > 0)
        self.assertTrue(keys_45.issubset(keys_46))
