import fnmatch
import io
import os
import signal
from unittest import mock

from selenium.common.exceptions import InvalidSelectorException

from cumulusci.tasks.robotframework import debugger


class TestDebugListener:
    @classmethod
    def setup_class(cls):
        cls.listener = debugger.DebugListener()

    def test_listener_default_breakpoint(self):
        """Verify we get the correct default breakpoint"""
        listener = debugger.DebugListener()
        assert len(listener.breakpoints) == 1
        bp = listener.breakpoints[0]
        assert not bp.temporary
        assert bp.pattern == "*::cumulusci.robotframework.Salesforce.Breakpoint"
        assert bp.breakpoint_type == debugger.Keyword
        assert bp.regex == fnmatch.translate(bp.pattern)

    def test_listener_custom_breakpoints(self):
        """Verify we can create a cli with custom breakpoints"""
        breakpoints = [
            debugger.Breakpoint(debugger.Keyword, "*::keyword breakpoint"),
            debugger.Breakpoint(debugger.Testcase, "*::test breakpoint"),
            debugger.Breakpoint(debugger.Suite, "*::suite breakpoint"),
        ]
        listener = debugger.DebugListener(*breakpoints)
        assert listener.breakpoints == breakpoints

    def test_listener_stack(self):
        """Verify that the listener properly tracks the stack as a test is executed"""
        self.listener.start_suite("Root", {"longname": "Root"})
        self.listener.start_suite("folder", {"longname": "Root.folder"})
        self.listener.start_suite("example", {"longname": "Root.folder.example"})
        self.listener.start_test("Test 1", {"longname": "Root.folder.example.Test 1"})
        self.listener.start_keyword("BuiltIn.Log", {"kwname": "Log"})

        # The listener stack should now include four elements, one for
        # each call to a listener method
        assert len(self.listener.stack) == 5

        assert self.listener.stack[0].name == "Root"
        assert self.listener.stack[1].name == "folder"
        assert self.listener.stack[2].name == "example"
        assert self.listener.stack[3].name == "Test 1"
        assert self.listener.stack[4].name == "BuiltIn.Log"

        # now, unwind the stack and make sure it's empty
        self.listener.end_keyword("BuiltIn.Log", {})
        self.listener.end_test("Test 1", {})
        self.listener.end_suite("example", {})
        self.listener.end_suite("folder", {})
        self.listener.end_suite("Root", {})
        assert len(self.listener.stack) == 0

    def test_listener_step(self):
        """Verify that the 'step' debugger command creates a breakpoint for the next step"""
        self.listener.start_suite("Root", {"longname": "Root"})
        self.listener.start_suite("example", {"longname": "Root.example"})
        self.listener.start_test("Test 1", {"longname": "Root.example.Test 1"})
        self.listener.start_keyword("cumulusci.Salesforce.breakpoint", {})

        assert (
            len(self.listener.breakpoints) == 1
        ), "Weird. There should have only been a single breakpoint"
        # call `do_step` of the *listener*, not the debugger UI.
        # the debugger ui "do_step" method will both add a new breakpoint
        # and then continue to that breakpoint, and then that breakpoint
        # will be removed. This test is verifying only that the breakpoing
        # is added
        self.listener.do_step()

        # The 'step' command should cause a new temporary breakpoint to be added
        # in the same context as the current keyword.
        assert (
            len(self.listener.breakpoints) == 2
        ), "Expected a breakpoint to be added on the 'step' command"
        assert self.listener.breakpoints[-1].pattern == "Root.example.Test 1::*"
        assert self.listener.breakpoints[-1].temporary

    def test_temporary_breakpoint(self):
        """Verify that a temporary breakpoint is removed when encountered"""
        bp1 = debugger.Breakpoint(debugger.Keyword, "*::breakpoint", temporary=False)
        bp2 = debugger.Breakpoint(
            debugger.Keyword, "*::temporary breakpoint", temporary=True
        )
        listener = debugger.DebugListener(bp1, bp2)
        listener.rdb = mock.Mock()
        # The listener uses the .intro attribute as a string, so
        # we need to set it to something so that the listener
        # doesnt' crash.
        listener.rdb.intro = "... intro ..."
        assert len(listener.breakpoints) == 2

        listener.start_suite("Suite", attrs={})
        listener.start_test("Test Case", attrs={})
        listener.start_keyword("temporary breakpoint", attrs={"args": ["one", "two"]})
        assert len(listener.breakpoints) == 1
        assert (
            listener.breakpoints[0].pattern == "*::breakpoint"
        ), "the wrong breakpoint was removed"
        listener.rdb.cmdloop.assert_called_once()


class TestRobotDebugger:
    """These tests are for the DebuggerCli class

    This class has methods of the form 'do_<something'> where
    <something> is a debugger command (step, continue, vars, etc).

    Instead of actually running robot with the debugger, these tests
    simply verify that each of those functions returns the right thing
    and calls the right functions.

    """

    def setup_method(self):
        self.mock_listener = mock.Mock()
        self.mock_builtin = mock.Mock()
        self.stdout = io.StringIO()
        self.cli = debugger.DebuggerCli(self.mock_listener, stdout=self.stdout)
        self.cli.builtin = self.mock_builtin

    def test_comment(self):
        """The comment command does nothing; we just need to verify
        that it returns None, which keeps the cmd REPL alive"""
        return_value = self.cli.default("# this is a comment")
        assert return_value is None

    def test_variable_shortcuts(self):
        """Verify that just passing a variable name to the debugger fetches the value of that variable"""
        # scalar variable
        return_value = self.cli.default("${varname}")
        self.mock_builtin.get_variable_value.assert_called_with("${varname}")
        assert return_value is None

        # list variable
        return_value = self.cli.default("@{varname}")
        self.mock_builtin.get_variable_value.assert_called_with("@{varname}")
        assert return_value is None

        # dictionary variable
        return_value = self.cli.default("&{varname}")
        self.mock_builtin.get_variable_value.assert_called_with("&{varname}")
        assert return_value is None

        # None of the above. Make sure we don't try to get the value
        # of something if it doesn't look like a variable
        return_value = self.cli.default("something")
        assert return_value is None
        self.mock_builtin.get_variable.value.assert_not_called()

        # valid variable syntax, but unknown variable
        self.cli.stdout = io.StringIO()
        self.mock_builtin.get_variable_value.side_effect = Exception("not a variable")
        return_value = self.cli.default("${bogus}")
        assert self.cli.stdout.getvalue() == "unknown variable '${bogus}'\n"

    @mock.patch("pdb.Pdb")
    def test_pdb(self, mock_pdb):
        """Verify that the 'pdb' command starts pdb"""
        self.cli.do_pdb("")
        mock_pdb.assert_has_calls(
            [mock.call(stdout=self.cli.stdout), mock.call().set_trace()]
        )

    def test_continue(self):
        """Verify that the 'continue' debugger command returns a truthy value

        The truthy value is what triggers the command processor to exit so
        that robot can continue.
        """
        return_value = self.cli.do_continue("")
        assert return_value

    def test_selenium(self):
        self.cli.selenium
        self.cli.builtin.get_library_instance.assert_called_with("SeleniumLibrary")

    @mock.patch.object(debugger.DebuggerCli, "selenium", mock.Mock())
    def test_locate_elements(self):
        """Test that the 'locate_elements' debugger command works

        This test sets up a mock that acts like selenium found several
        elements, and verifies that it calls the functions to highlight them
        """
        self.cli._highlight_element = mock.Mock()
        self.cli.selenium.get_webelements.return_value = ["Element1", "Element2"]
        return_value = self.cli.do_locate_elements("//whatever")
        assert return_value is None
        self.cli._highlight_element.assert_has_calls(
            [mock.call("Element1"), mock.call("Element2")]
        )
        assert self.cli.stdout.getvalue() == "Found 2 matches\n"

    @mock.patch.object(debugger.DebuggerCli, "selenium", mock.Mock())
    def test_locate_elements_exception_handling(self):
        """Verify that the 'locate_elements' debugger command handles exceptions"""

        self.cli._highlight_element = mock.Mock()
        self.cli.selenium.get_webelements.side_effect = InvalidSelectorException(
            "invalid xpath"
        )
        self.cli.stdout = io.StringIO()
        return_value = self.cli.do_locate_elements("//whatever")
        assert return_value is None
        self.cli._highlight_element.assert_not_called()
        assert self.cli.stdout.getvalue() == "invalid locator '//whatever'\n"

        # Even if get_webelement throws an exception, the keyword
        # should handle it gracefully
        self.cli.selenium.get_webelements.side_effect = Exception(
            "something unexpected"
        )
        self.cli.stdout = io.StringIO()
        return_value = self.cli.do_locate_elements("//whatever")
        assert return_value is None
        self.cli._highlight_element.assert_not_called()
        assert self.cli.stdout.getvalue() == "something unexpected\n"

    @mock.patch.object(debugger.DebuggerCli, "selenium", mock.Mock())
    def test_highlight_element_executes_javascript(self):
        mock_element = mock.Mock()
        mock_element.get_attribute.return_value = ""
        self.cli._highlight_element(mock_element)
        self.cli.selenium.driver.execute_script.assert_called()

    @mock.patch.object(debugger.DebuggerCli, "selenium", mock.Mock())
    def test_reset_elements(self):
        """Verify that the 'reset_elements' debugger command works"""
        self.cli._restore_element_style = mock.Mock()
        self.cli.selenium.get_webelements.return_value = ["Element1", "Element2"]
        return_value = self.cli.do_reset_elements("")
        assert return_value is None
        self.cli._restore_element_style.assert_has_calls(
            [mock.call("Element1"), mock.call("Element2")]
        )

    @mock.patch.object(debugger.DebuggerCli, "selenium", mock.Mock())
    def test_reset_elements_logging(self):
        self.cli.selenium.driver.execute_script.return_value = False
        self.cli._restore_element_style("dummy")
        self.cli.builtin.log.assert_called_with(
            "unable to restore style; original style not found", "DEBUG"
        )

    def test_shell_no_variables(self):
        """Verify that the shell command works"""
        with mock.patch.object(
            self.mock_builtin, "run_keyword_and_ignore_error", return_value=("PASS", 42)
        ):
            return_value = self.cli.do_shell("some keyword")
            assert return_value is None
            assert not self.mock_builtin.set_test_variable.called

    def test_shell_one_variable(self):
        """Verify that the shell command can set a single variable"""
        with mock.patch.object(
            self.mock_builtin, "run_keyword_and_ignore_error", return_value=("PASS", 42)
        ):

            return_value = self.cli.do_shell(
                "${value}  get variable value  ${whatever}"
            )
            assert return_value is None

            self.mock_builtin.run_keyword_and_ignore_error.assert_called_with(
                "get variable value", "${whatever}"
            )
            self.mock_builtin.set_test_variable.assert_called_with("${value}", 42)

    def test_shell_fail(self):
        """Verify that if a shell command fails, variables aren't set"""
        with mock.patch.object(
            self.mock_builtin,
            "run_keyword_and_ignore_error",
            return_value=("FAIL", (None,)),
        ):
            return_value = self.cli.do_shell(
                "${value1}  ${value2}   some keyword  ${whatever}"
            )
            assert return_value is None

            self.mock_builtin.set_test_variable.assert_not_called()

    def test_shell_two_variables(self):
        """Verify that the shell command can set more than one variable"""
        with mock.patch.object(
            self.mock_builtin,
            "run_keyword_and_ignore_error",
            return_value=("PASS", ("Inigo", "Montoya")),
        ):
            return_value = self.cli.do_shell(
                "${value1}  ${value2}   some keyword  ${whatever}"
            )
            assert return_value is None

            self.mock_builtin.set_test_variable.assert_has_calls(
                [mock.call("${value1}", "Inigo"), mock.call("${value2}", "Montoya")]
            )

    def test_shell_exception(self):
        with mock.patch.object(
            self.mock_builtin,
            "run_keyword_and_ignore_error",
            side_effect=Exception("Danger, Will Robinson!"),
        ):
            self.cli.do_shell("${value1}  ${value2}   some keyword  ${whatever}")
            assert (
                self.cli.stdout.getvalue()
                == "error running keyword: Danger, Will Robinson!\n"
            )

    def test_step(self):
        """Test the 'step' debugger command"""
        # unlike most other commands, this one returns True
        # to allow the debugger to continue. We also need to verify
        # That the number of breakpoints after the step is the
        # same as before the step
        return_value = self.cli.do_step("")
        assert return_value is True
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
        assert return_value is None

        # FIXME: add assertions to prove that the listener is
        # keeping track of the stack

    @mock.patch("cumulusci.tasks.robotframework.debugger.ui.CliTable")
    def test_vars(self, mock_clitbl):
        """Test the 'vars' debugger command"""
        self.mock_builtin.get_variables.return_value = {"one": 1, "two": 2}
        self.cli.do_vars("")
        mock_clitbl.assert_called_with([["Variable", "Value"], ["one", 1], ["two", 2]])
        mock_clitbl.return_value.echo.assert_called()

    def test_quit(self):
        with mock.patch("os.kill") as mock_kill:
            self.cli.do_quit("")
            mock_kill.assert_called_with(os.getpid(), signal.SIGTERM)


class TestInternalModels:
    def test_testcase(self):
        testcase = debugger.Testcase(
            name="Test Case #1", attrs={"longname": "Root.Test Case #1"}
        )
        assert repr(testcase) == "<Testcase: Test Case #1>"

        # robot passes in a longname, so make sure the property reflects it
        assert testcase.longname == "Root.Test Case #1"

    def test_keyword(self):
        keyword = debugger.Keyword(name="Keyword #1", attrs={"args": ["foo", "bar"]})
        assert repr(keyword) == "<Keyword: Keyword #1  foo  bar>"
        # robot will NOT pass in a longname; make sure the property handles that case
        assert keyword.longname == keyword.name

    def test_suite(self):
        suite = debugger.Suite(
            name="Suite #1", attrs={"source": "test.robot", "longname": "Root.Suite #1"}
        )
        assert repr(suite) == "<Suite: Suite #1 (test.robot)>"
        # robot passes in a longname, so make sure the property reflects it
        assert suite.longname == "Root.Suite #1"

    def test_breakpoint_match(self):
        bp = debugger.Breakpoint(debugger.Keyword, "*::breakpoint")
        assert bp.match(
            context="Suite.Test Case::breakpoint"
        ), "expected breakpoint to match, but it didn't"
        assert not bp.match(
            context="Suite.Test Case::some other keyword"
        ), "didn't expect breakpoint to match, but it did"
