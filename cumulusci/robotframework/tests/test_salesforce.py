from unittest import mock

import pytest
from SeleniumLibrary.errors import ElementNotFound

from cumulusci.robotframework.Salesforce import Salesforce
from selenium.common.exceptions import StaleElementReferenceException


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


@mock.patch("robot.libraries.BuiltIn.BuiltIn._get_context")
class TestKeywordGetAllPicklistValues:
    @classmethod
    def setup_class(cls):
        cls.sflib = Salesforce(locators={"body": "//whatever"})

    def test_returns_rendered_picklist_values(self, mock_robot_context):
        option_1 = mock.Mock(text="Warm")
        option_2 = mock.Mock(text="Cold")
        option_3 = mock.Mock(text="Warm")
        option_4 = mock.Mock(text="   ")

        with mock.patch.object(self.sflib, "scroll_element_into_view"):
            self.sflib.selenium.get_webelements.return_value = [
                option_1,
                option_2,
                option_3,
                option_4,
            ]

            values = self.sflib.get_all_picklist_values("Status")

        assert values == ["Warm", "Cold", "Warm", ""]
        self.sflib.selenium.wait_until_element_is_visible.assert_called_once()
        self.sflib.selenium.press_keys.assert_any_call(None, "ESC")

    def test_ignores_stale_options(self, mock_robot_context):
        good_option = mock.Mock(text="Active")

        stale_option = mock.Mock()
        type(stale_option).text = mock.PropertyMock(
            side_effect=StaleElementReferenceException()
        )

        with mock.patch.object(self.sflib, "scroll_element_into_view"):
            self.sflib.selenium.get_webelements.return_value = [
                stale_option,
                good_option,
            ]

            values = self.sflib.get_all_picklist_values("Status")

        assert values == ["Active"]

    def test_raises_assertion_when_picklist_not_found(self, mock_robot_context):
        self.sflib.selenium.set_focus_to_element.side_effect = ElementNotFound()

        with pytest.raises(
            AssertionError,
            match="Picklist 'Status' was not found on the page.",
        ):
            self.sflib.get_all_picklist_values("Status")

    def test_uses_custom_timeout(self, mock_robot_context):
        option = mock.Mock(text="Active")

        with mock.patch.object(self.sflib, "scroll_element_into_view"):
            self.sflib.selenium.get_webelements.return_value = [option]

            self.sflib.get_all_picklist_values("Status", timeout="15s")

        _, kwargs = self.sflib.selenium.wait_until_element_is_visible.call_args
        assert kwargs["timeout"] == "15s"