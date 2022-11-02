import io
from unittest import mock

from cumulusci.tasks.robotframework import debugger
from cumulusci.tasks.robotframework.debugger.ui import (
    BrowserProxy,
    SeleniumProxy,
    initialize_highlight_js,
)

"""
These tests verify that the proxy used by the debugger uses
the appropriate javascript methods for the given browser library
"""


class StringContaining(str):
    """Used for fuzzy assertions"""

    def __eq__(self, other):
        return self in other


class TestSeleniumProxy:
    @classmethod
    def setup_class(cls):
        cls.selenium = mock.Mock()
        cls.proxy = SeleniumProxy(cls.selenium)

    def setup_method(self):
        self.mock_listener = mock.Mock()
        self.mock_builtin = mock.Mock()
        self.stdout = io.StringIO()
        self.cli = debugger.DebuggerCli(self.mock_listener, stdout=self.stdout)
        self.cli.builtin = self.mock_builtin
        self.selenium.reset_mock()

    def test_webbrowser_browser(self):
        """Verify the cli has initialized the webbrowser attribute to SeleniumProxy

        ... but only Browser has been loaded and SeleniumLibrary has not
        """
        self.cli.builtin.get_library_instance = mock.Mock(
            return_value={
                "SeleniumLibrary": mock.Mock(),
                "Browser": mock.Mock(),
            }
        )
        assert isinstance(self.cli.webbrowser, SeleniumProxy)

    def test_highlight_injected_css(self):
        """Verify we attempt to inject css into the DOM when highlighting an element"""

        self.selenium.get_webelements = mock.Mock(return_value=[])
        self.proxy.highlight_elements("button")

        self.selenium.driver.execute_script.assert_any_call(initialize_highlight_js)

    def test_highlight_element(self):
        """Verify we attempt to add the custom css to matching elements"""

        element1 = mock.Mock()
        element2 = mock.Mock()
        self.selenium.get_webelements = mock.Mock(return_value=[element1, element2])

        self.proxy.highlight_elements("button")
        # expect 3 calls to execute javascript: once for the initialization
        # and one for each element we find
        assert len(self.selenium.driver.execute_script.mock_calls) == 3
        self.selenium.driver.execute_script.assert_any_call(
            "arguments[0].classList.add('rdbHighlight');", element1
        )
        self.selenium.driver.execute_script.assert_any_call(
            "arguments[0].classList.add('rdbHighlight');", element2
        )


class TestBrowserProxy:
    @classmethod
    def setup_class(cls):
        cls.browser = mock.Mock()
        cls.proxy = BrowserProxy(cls.browser)

    def setup_method(self):
        self.mock_listener = mock.Mock()
        self.mock_builtin = mock.Mock()
        self.stdout = io.StringIO()
        self.cli = debugger.DebuggerCli(self.mock_listener, stdout=self.stdout)
        self.cli.builtin = self.mock_builtin
        self.browser.reset_mock()

    def test_webbrowser_browser(self):
        """Verify the cli has initialized the webbrowser attribute to BrowserProxy

        ... but only Browser has been loaded and SeleniumLibrary has not
        """
        self.cli.builtin.get_library_instance = mock.Mock(
            return_value={
                "Browser": mock.Mock(),
            }
        )
        assert isinstance(self.cli.webbrowser, BrowserProxy)

    def test_highlight_injected_css(self):
        """Verify we attempt to inject css into the DOM when highlighting an element"""
        script = f"() => {{{initialize_highlight_js}}};"
        self.browser.get_elements = mock.Mock(return_value=[])
        self.proxy.highlight_elements("button")
        self.browser.evaluate_javascript.assert_any_call(None, script)

    def test_highlight_element(self):
        """Verify that we call evaluate some javascript that applies the class to every matching element"""
        element1 = mock.Mock()
        element2 = mock.Mock()
        self.browser.get_elements = mock.Mock(return_value=[element1, element2])

        self.proxy.highlight_elements("button")
        script = """(elements) => {
                    for (element of elements) {
                        element.classList.add('rdbHighlight')
                    }
                }"""

        self.browser.evaluate_javascript.assert_any_call(
            "button", script, all_elements=True
        )

    def test_restore_element_style(self):
        self.proxy.restore_element_style()
        script = """(elements) => {
                for (element of elements) {
                    element.classList.remove('rdbHighlight')
                }
            }"""
        self.browser.evaluate_javascript.assert_called_with(
            ".rdbHighlight", script, all_elements=True
        )
