import unittest
from unittest import mock
from pathlib import Path
import tempfile
import shutil

import cumulusci.robotframework.utils as robot_utils
from cumulusci.utils import touch


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


class TestGetLocatorModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # get_locator_module uses __file__ to locate the locator
        # module. We'll point it to a temporary directory so that
        # we can control what files we test against.

        cls.tempdir = Path(tempfile.mkdtemp())
        # sorted alphabetically, 5 should come after 40. The
        # code should be sorting numerically so that 5 comes
        # before 40. That's why "locators_5.py" is here.
        touch(Path(cls.tempdir, "locators_5.py"))
        touch(Path(cls.tempdir, "locators_39.py"))
        touch(Path(cls.tempdir, "locators_40.py"))

        dunder_file = Path(cls.tempdir, "utils.py").absolute()
        cls.patched_utils = mock.patch.object(robot_utils, "__file__", dunder_file)
        cls.patched_utils.start()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tempdir)
        cls.patched_utils.stop()

    def test_get_locator_module_name_no_version(self):
        """Verify that we get the latest version if we don't have a version number"""
        module_name = robot_utils.get_locator_module_name(None)
        assert module_name == "cumulusci.robotframework.locators_40"

    def test_get_locator_module_name_specific_version(self):
        """Verify that we get the specific version we ask for"""
        for version in (5, 39, 40):
            actual_module_name = robot_utils.get_locator_module_name(version)
            expected_module_name = f"cumulusci.robotframework.locators_{version}"
            assert expected_module_name == actual_module_name

    def test_get_locator_module_name_version_too_low(self):
        """Verify that we get the latest version if version specified isn't supported"""
        module_name = robot_utils.get_locator_module_name(37)
        assert module_name == "cumulusci.robotframework.locators_40"

    def test_get_locator_module_name_version_too_high(self):
        """Verify that we get the latest version if version specified isn't supported"""
        module_name = robot_utils.get_locator_module_name(41)
        assert module_name == "cumulusci.robotframework.locators_40"
