import unittest
from unittest import mock

import cumulusci.robotframework.utils as robot_utils


class TestRobotframeworkUtils(unittest.TestCase):
    def setUp(self):
        robot_utils.BuiltIn = mock.Mock(name="BuiltIn")
        self.mock_selib = robot_utils.BuiltIn().get_library_instance("SeleniumLibrary")

    def test_screenshot_decorator_fail(self):
        """Verify that the decorator will capture a screenshot on keyword failure"""

        @robot_utils.capture_screenshot_on_error
        def example_function():
            raise Exception("Danger Will Robinson!")

        try:
            example_function()
        except Exception:
            pass
        self.mock_selib.failure_occurred.assert_called_once()

    def test_screenshot_decorator_pass(self):
        """Verify that decorator does NOT capture screenshot on keyword success"""

        @robot_utils.capture_screenshot_on_error
        def example_function():
            return True

        example_function()
        self.mock_selib.failure_occurred.assert_not_called()
