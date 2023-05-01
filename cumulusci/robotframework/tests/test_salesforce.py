from unittest import mock

import pytest
from SeleniumLibrary.errors import ElementNotFound

from cumulusci.robotframework.Salesforce import Salesforce


# _init_locators has a special code block
class TestSeleniumLibrary:
    def test_init_locators(self):
        """Verify that locators are initialized if not passed in"""
        with mock.patch.object(Salesforce, "_init_locators"):
            # _init_locators should NOT be called if we pass them in
            sflib = Salesforce(locators={"body": "//whatever"})
            assert not sflib._init_locators.called

            # _init_locators SHOULD be called if we don't pass them in
            sflib = Salesforce()
            sflib._init_locators.assert_called_once()


@mock.patch("robot.libraries.BuiltIn.BuiltIn._get_context")
class TestKeyword_wait_until_salesforce_is_ready:
    @classmethod
    def setup_class(cls):
        cls.sflib = Salesforce(locators={"body": "//whatever"})

    def test_successful_page_load(self, mock_robot_context):
        """Verify that a succesful page load returns no errors"""
        with mock.patch.object(Salesforce, "wait_for_aura", return_value=True):
            self.sflib.wait_until_salesforce_is_ready(timeout="1")

            self.sflib.wait_for_aura.assert_called_once()
            self.sflib.selenium.get_webelement.assert_called_once_with("//whatever")

    def test_reload_on_initial_failure(self, mock_robot_context):
        """Verify that we attempt a reload when we don't find the lightning component"""
        with mock.patch.object(Salesforce, "wait_for_aura", return_value=True):
            with mock.patch.object(
                Salesforce, "_check_for_classic", return_value=False
            ):
                with mock.patch.object(
                    Salesforce, "_check_for_login_failure", return_value=False
                ):
                    with mock.patch.object(
                        self.sflib.selenium,
                        "get_webelement",
                        side_effect=(ElementNotFound(), True),
                    ):
                        self.sflib.wait_until_salesforce_is_ready(timeout="10")
                        self.sflib.selenium.go_to.assert_called_once()

    def test_exception_and_screenshot_on_timeout(self, mock_robot_context):
        """Verify that we throw an appropriate exception after the timeout"""
        with mock.patch.object(Salesforce, "wait_for_aura", return_value=True):
            self.sflib.selenium.get_webelement.side_effect = ElementNotFound()

            with pytest.raises(
                Exception, match="Timed out waiting for a lightning page"
            ):
                # The timeout needs to be longer than the duration of
                # one loop iteration, but less than the retry interval
                # of 5 seconds. Making it longer should still pass the
                # test, it just makes the test run longer than necessary.
                self.sflib.wait_until_salesforce_is_ready(timeout=0.1)

            self.sflib.selenium.capture_page_screenshot.assert_called()


@mock.patch("robot.libraries.BuiltIn.BuiltIn._get_context")
class TestKeyword_breakpoint:
    @classmethod
    def setup_class(cls):
        cls.sflib = Salesforce(locators={"body": "//whatever"})

    def test_breakpoint(self, mock_robot_context):
        """Verify that the keyword doesn't raise an exception"""
        assert self.sflib.breakpoint() is None
