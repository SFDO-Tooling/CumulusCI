import mock
import unittest
from cumulusci.tasks.robotframework import debugger
from selenium.common.exceptions import InvalidSelectorException


class TestDebugListener(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestDebugListener, cls).setUpClass()
        cls.listener = debugger.DebugListener()

    def test_listener_stack(self):
        """Verify that the listener properly tracks the stack as a test is executed"""
        self.listener.start_suite("Root", {"longname": "Root"})
        self.listener.start_suite("folder", {"longname": "Root.folder"})
        self.listener.start_suite("example", {"longname": "Root.folder.example"})
        self.listener.start_test("Test 1", {"longname": "Root.folder.example.Test 1"})
        self.listener.start_keyword("BuiltIn.Log", {"kwname": "Log"})

        # The listener stack should now include four elements, one for
        # each call to a listener method
        self.assertEquals(len(self.listener.stack), 5)

        self.assertEquals(self.listener.stack[0].name, "Root")
        self.assertEquals(self.listener.stack[1].name, "folder")
        self.assertEquals(self.listener.stack[2].name, "example")
        self.assertEquals(self.listener.stack[3].name, "Test 1")
        self.assertEquals(self.listener.stack[4].name, "BuiltIn.Log")

        # now, unwind the stack and make sure it's empty
        self.listener.end_keyword("BuiltIn.Log", {})
        self.listener.end_test("Test 1", {})
        self.listener.end_test("example", {})
        self.listener.end_test("folder", {})
        self.listener.end_test("Root", {})
        self.assertEquals(len(self.listener.stack), 0)

    def test_listener_step(self):
        """Verify that the 'step' debugger command creates a breakpoint for the next step"""
        self.listener.start_suite("Root", {"longname": "Root"})
        self.listener.start_suite("example", {"longname": "Root.example"})
        self.listener.start_test("Test 1", {"longname": "Root.example.Test 1"})
        self.listener.start_keyword("cumulusci.Salesforce.breakpoint", {})

        self.assertEqual(
            len(self.listener.breakpoints),
            1,
            "Weird. There should have only been a single breakpoint",
        )
        # call `do_step` of the *listener*, not the debugger UI.
        # the debugger ui "do_step" method will both add a new breakpoint
        # and then continue to that breakpoint, and then that breakpoint
        # will be removed. This test is verifying only that the breakpoing
        # is added
        self.listener.do_step()

        # The 'step' command should cause a new temporary breakpoint to be added
        # in the same context as the current keyword.
        self.assertEqual(
            len(self.listener.breakpoints),
            2,
            "Expected a breakpoint to be added on the 'step' command",
        )
        self.assertEqual(
            self.listener.breakpoints[-1].pattern, "Root.example.Test 1::*"
        )
        self.assertTrue(self.listener.breakpoints[-1].temporary)


class TestRobotDebugger(unittest.TestCase):
    """These tests are for the DebuggerCli class

    This class has methods of the form 'do_<something'> where
    <something> is a debugger command (step, continue, vars, etc).

    Instead of actually running robot with the debugger, these tests
    simply verify that each of those functions returns the right thing
    and calls the right functions.

    """

    @classmethod
    def setUpClass(cls):
        super(TestRobotDebugger, cls).setUpClass()
        cls.mock_listener = mock.Mock()
        cls.mock_builtin = mock.Mock()
        cls.cli = debugger.DebuggerCli(cls.mock_listener)
        cls.cli.builtin = cls.mock_builtin

    def test_comment(self):
        """The comment command does nothing; we just need to verify
        that it returns None, which keeps the cmd REPL alive"""
        return_value = self.cli.default("# this is a comment")
        self.assertEquals(return_value, None)

    def test_variable_shortcuts(self):
        """Verify that just passing a variable name to the debugger fetches the value of that variable"""
        # scalar variable
        return_value = self.cli.default("${varname}")
        self.mock_builtin.get_variable_value.assert_called_with("${varname}")
        self.assertIsNone(return_value)

        # list variable
        return_value = self.cli.default("@{varname}")
        self.mock_builtin.get_variable_value.assert_called_with("@{varname}")
        self.assertIsNone(return_value)

        # dictionary variable
        return_value = self.cli.default("&{varname}")
        self.mock_builtin.get_variable_value.assert_called_with("&{varname}")
        self.assertIsNone(return_value)

        # None of the above. Make sure we don't try to get the value
        # of something if it doesn't look like a variable
        return_value = self.cli.default("something")
        self.assertIsNone(return_value)
        self.mock_builtin.get_variable.value.assert_not_called()

    def test_continue(self):
        """Verify that the 'continue' debugger command returns a truthy value

        The truthy value is what triggers the command processor to exit so
        that robot can continue.
        """
        return_value = self.cli.do_continue("")
        self.assertTrue(return_value)

    def test_locate_elements(self):
        """Test that the 'locate_elements' debugger command works

        This test sets up a mock that acts like selenium found several
        elements, and verifies that it calls the functions to highlight them
        """
        with mock.patch.object(
            debugger.DebuggerCli, "selenium", mock.Mock()
        ) as mock_selenium:
            self.cli._highlight_element = mock.Mock()
            mock_selenium.get_webelements.return_value = ["Element1", "Element2"]
            return_value = self.cli.do_locate_elements("//whatever")
            self.assertIsNone(return_value)
            self.cli._highlight_element.assert_has_calls(
                [mock.call("Element1"), mock.call("Element2")]
            )

    def test_locate_elements_exception_handling(self):
        """Verify that the 'locate_elements' debugger command handles exceptions"""

        with mock.patch.object(
            debugger.DebuggerCli, "selenium", mock.Mock()
        ) as mock_selenium:
            self.cli._highlight_element = mock.Mock()

            mock_selenium.get_webelements.side_effect = InvalidSelectorException(
                "invalid xpath"
            )
            return_value = self.cli.do_locate_elements("//whatever")
            self.assertIsNone(return_value)
            self.cli._highlight_element.assert_not_called()

            mock_selenium.get_webelements.side_effect = Exception(
                "something unexpected"
            )
            return_value = self.cli.do_locate_elements("//whatever")
            self.assertIsNone(return_value)
            self.cli._highlight_element.assert_not_called()

    def test_reset_elements(self):
        """Verify that the 'reset_elements' debugger command works"""
        with mock.patch.object(
            debugger.DebuggerCli, "selenium", mock.Mock()
        ) as mock_selenium:
            self.cli._restore_element_style = mock.Mock()
            mock_selenium.get_webelements.return_value = ["Element1", "Element2"]
            return_value = self.cli.do_reset_elements("")
            self.assertIsNone(return_value)
            self.cli._restore_element_style.assert_has_calls(
                [mock.call("Element1"), mock.call("Element2")]
            )

    def test_shell_no_variables(self):
        """Verify that the shell command works"""
        self.mock_builtin.run_keyword_and_ignore_error.return_value = ("PASS", 42)

        return_value = self.cli.do_shell("some keyword")
        self.assertIsNone(return_value)
        assert not self.mock_builtin.set_test_variable.called

    def test_shell_one_variable(self):
        """Verify that the shell command can set a single variable"""
        self.mock_builtin.run_keyword_and_ignore_error.return_value = ("PASS", 42)

        return_value = self.cli.do_shell("${value}  get variable value  ${whatever}")
        self.assertIsNone(return_value)

        self.mock_builtin.run_keyword_and_ignore_error.assert_called_with(
            "get variable value", "${whatever}"
        )
        self.mock_builtin.set_test_variable.assert_called_with("${value}", 42)

    def test_shell_two_variables(self):
        """Verify that the shell command can set more than one variable"""
        self.mock_builtin.run_keyword_and_ignore_error.return_value = (
            "PASS",
            ("Inigo", "Montoya"),
        )

        return_value = self.cli.do_shell(
            "${value1}  ${value2}   some keyword  ${whatever}"
        )
        self.assertIsNone(return_value)

        self.mock_builtin.set_test_variable.assert_has_calls(
            [mock.call("${value1}", "Inigo"), mock.call("${value2}", "Montoya")]
        )

        # FIXME: need to add a test case for shell where a keyword that throws an error
        # that requires examining stdout, which I haven't got working just yet...

    def test_step(self):
        """Test the 'step' debugger command"""
        # unlike most other commands, this one returns True
        # to allow the debugger to continue. We also need to verify
        # That the number of breakpoints after the step is the
        # same as before the step
        return_value = self.cli.do_step("")
        self.assertEqual(return_value, True)
        self.mock_listener.do_step.assert_called()

    def test_where(self):
        """Test the 'where' debugger command"""
        self.mock_listener.stack = [
            debugger.Suite(name="Suite", attrs={}),
            debugger.Suite(name="Another Suite", attrs={}),
            debugger.Testcase(name="Testcase", attrs={}),
            debugger.Keyword(name="A keyword", attrs={}),
        ]
        return_value = self.cli.do_where("")
        self.assertIsNone(return_value)

        # FIXME: add assertions to prove that the listener is
        # keeping track of the stack

    @mock.patch("cumulusci.tasks.robotframework.debugger.ui.CliTable")
    def test_vars(self, mock_clitbl):
        """Test the 'vars' debugger command"""
        self.mock_builtin.get_variables.return_value = {"one": 1, "two": 2}
        self.cli.do_vars("")
        mock_clitbl.assert_called_with([["Variable", "Value"], ["one", 1], ["two", 2]])
        mock_clitbl.return_value.echo.assert_called()
