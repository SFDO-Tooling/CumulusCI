import cmd
import os
import pdb
import re
import signal
import sys
import textwrap

from robot.libraries.BuiltIn import BuiltIn
from selenium.common.exceptions import InvalidSelectorException

from cumulusci.cli.ui import CliTable


class DebuggerCli(cmd.Cmd, object):
    intro = textwrap.dedent(
        """
        :::
        ::: Welcome to rdb, the Robot Framework debugger
        :::

        Type help or ? to list commands.
    """
    )
    prompt = "rdb> "

    # Robot redirects sys.stdout, so use the original handle
    # or whatever is passed in.
    def __init__(self, listener, stdout=sys.__stdout__):

        cmd.Cmd.__init__(self, stdout=stdout)

        self.listener = listener
        self.builtin = BuiltIn()

        # some simple aliases.
        self.do_c = self.do_continue
        self.do_le = self.do_locate_elements
        self.do_s = self.do_step

    @property
    def selenium(self):
        return self.builtin.get_library_instance("SeleniumLibrary")

    def default(self, line):
        """Ignore lines that begin with #"""

        if line.startswith("#"):
            return

        elif re.match(r"^[$@&]\{.*\}$", line):
            try:
                value = self.builtin.get_variable_value(line)
                print(value, file=self.stdout)
            except Exception:
                print("unknown variable '{}'".format(line), file=self.stdout)

        else:
            super(DebuggerCli, self).default(line)

    def do_continue(self, arg=None):
        """Let the test continue"""
        return True

    def do_locate_elements(self, locator):
        """Find and highlight all elements that match the given selenium locator

        Example:

            rdb> locate_elements //button[@title='Learn More']
        """
        try:
            elements = self.selenium.get_webelements(locator)
            print("Found {} matches".format(len(elements)), file=self.stdout)
            for element in elements:
                self._highlight_element(element)

        except InvalidSelectorException:
            print("invalid locator '{}'".format(locator), file=self.stdout)

        except Exception as e:
            print(str(e), file=self.stdout)

    def do_pdb(self, arg=None):
        """Start pdb

        The context will be this function, which won't be particularly
        useful. This is mostly for debugging the debug code. How meta!
        """

        pdb.Pdb(stdout=self.stdout).set_trace()

    def do_quit(self, arg=None):
        """Cause robot to quit gracefully (all remaining tests will be skipped)"""
        os.kill(os.getpid(), signal.SIGTERM)
        return True

    def do_reset_elements(self, arg=None):
        """Remove all highlighting added by `locate_elements`"""
        elements = self.selenium.get_webelements("//*[@data-original-style]")
        for element in elements:
            self._restore_element_style(element)

    def do_shell(self, arg):
        """
        Execute a robot framework keyword. (shortcut: !)

        The statement should be formatted just like in a .robot
        file, with two spaces between each argument.

        Example:

            rdb> shell log  hello, world
            -or-
            rdb> ! log  hello, world

        Variables can be specified the same as in a robot file. For
        example, this will set a test variable named ${location}:

            rdb> shell ${location}  get location
        """

        # Split into words with multiple spaces as a separator, then
        # pull out any leading varibles before running the command.
        words = re.split(" {2,}", arg)
        vars = []
        for word in words:
            if re.match(r"[\$@&]\{.*?\}\s*=?", word):
                vars.append(word.rstrip("="))
            else:
                break
        statement = words[len(vars) :]

        try:
            status, result = self.builtin.run_keyword_and_ignore_error(*statement)
            print("status: {}".format(status), file=self.stdout)
            if not vars or status == "FAIL":
                print("result: {}".format(result), file=self.stdout)

            else:
                # Assign test variables given on the command line
                # I don't think this is exactly how robot does it,
                # but I think it's good enough for all normal cases.
                if len(vars) == 1:
                    self.builtin.set_test_variable(vars[0], result)
                    print("{} was set to {}".format(vars[0], result), file=self.stdout)
                else:
                    for (varname, value) in zip(vars, result):
                        self.builtin.set_test_variable(varname, value)
                        print(
                            "{} was set to {}".format(varname, value), file=self.stdout
                        )

        except Exception as e:
            print("error running keyword: {}".format(e), file=self.stdout)

    def do_step(self, arg=None):
        """Run the next step in the test

        This will run the line where the test is currently paused, and then
        stop at the next keyword in the same test case.
        """
        self.listener.do_step()
        return True

    def do_vars(self, arg=None):
        """Print the value of all known variables"""
        vars = self.builtin.get_variables()
        vars = [["Variable", "Value"]] + [list(x) for x in sorted(vars.items())]
        CliTable(vars).echo()

    def do_where(self, arg=None):
        """
        Print the current robot stack (hierarchy of suites and tests,
        ending with the current keyword
        """

        prefix = "  "
        for i, x in enumerate(self.listener.stack):
            indent = prefix * i
            print("{}: {}-> {}".format(i, indent, x.longname), file=self.stdout)
        print("", file=self.stdout)

    def _highlight_element(self, element):
        """Highlight a Selenium Webdriver element

        This works by replacing the `style` attribute of the element with
        a custom style. The original style is saved in a custom attribute
        named `data-original-style`, which is used by _restore_element_style.

        If the element already has a data-original-style attribute it will
        not be overwritten.
        """

        element_style = """
            box-shadow: 0px 1px 4px 2px inset #FFFF00;
        """
        original_style = element.get_attribute("style")
        new_style = original_style + element_style
        self.selenium.driver.execute_script(
            """
            if (!arguments[0].hasAttribute("data-original-style")) {
                console.log('adding data-original-style...');
                /* only save the original style if we haven't already done so */
                arguments[0].setAttribute('data-original-style', arguments[0].getAttribute('style'));
            };
            arguments[0].setAttribute('style', arguments[1]);

        """,
            element,
            new_style,
        )

    def _restore_element_style(self, element):
        """Restore the element style from the data-original-style attribute

        This is to undo the effects of _highlight_element
        """
        js = """
        if (arguments[0].hasAttribute('data-original-style')) {
            var original_style = arguments[0].getAttribute('data-original-style');
            arguments[0].setAttribute('style', original_style);
            arguments[0].removeAttribute('data-original-style');
            return true;
        } else {
            return false;
        }
        """

        result = self.selenium.driver.execute_script(js, element)
        if result is False:
            self.builtin.log(
                "unable to restore style; original style not found", "DEBUG"
            )
        return result
