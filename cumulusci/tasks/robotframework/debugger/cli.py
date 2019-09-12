import cmd
import textwrap
import os
import sys
import re
from robot.libraries.BuiltIn import BuiltIn
from cumulusci.cli.ui import CliTable


class DebuggerCli(cmd.Cmd):
    intro = textwrap.dedent(
        """\
        Welcome to rdb, the Robot Framework debugger

        Type help or ? to list commands.
    """
    )
    prompt = "rdb> "

    def __init__(self, listener):

        # robot redirects sys.stdout, use the orig version
        cmd.Cmd.__init__(self, stdout=sys.__stdout__)

        self.listener = listener
        if os.getenv("EMACS", False):
            # N.B. running a shell inside of emacs sets this environment
            # variable. Handy, because when running in a shell inside emacs
            # we need to turn off raw input
            self.use_rawinput = False

        # allow some simple aliases
        self.do_c = self.do_continue

    @property
    def selenium(self):
        return BuiltIn().get_library_instance("SeleniumLibrary")

    def _run_robot_statement(self, line):
        ## 1. split on spaces
        words = re.split(" {2,}", line)

        ## 2. separate out variables
        vars = []
        for word in words:
            if re.match(r"${.*?}"):
                vars.append(word)
            else:
                break

        ## 3. run command
        status, value = BuiltIn().run_keyword_and_ignore_error(*words)

        ## 4. assign variables

    def default(self, line):
        """Ignore lines that begin with #"""

        if line.startswith("#"):
            return

        elif re.match(r"^\$\{.*\}", line):
            try:
                value = BuiltIn().get_variable_value(line)
                print(value)
            except Exception:
                print("unknown variable '{}'".format(line))

        else:
            super().default(line)

    def do_pdb(self, arg):
        """Start pdb

        The context will be this function, which won't be particularly
        useful. This is mostly for debugging the debug code. How meta!
        """
        import pdb

        pdb.Pdb(stdout=sys.__stdout__).set_trace()

    def do_continue(self, arg):
        """Let the test continue"""
        return True

    def do_step(self, arg):
        # ok, what we have to do is tell the listener to
        # stop at the next keyword somehow...
        self.listener.do_step()
        return True

    def do_vars(self, arg):
        """Print the value of all known variables"""
        vars = BuiltIn().get_variables()
        vars = [["Variable", "Value"]] + [x for x in map(list, vars.items())]
        CliTable(vars).echo()

    def do_shell(self, arg):
        """
        Execute a robot framework keyword.

        The statement should be formatted just line in a .robot
        file, with two spaces between each argument.

        Example:

            rdb> eval log  hello, world
        """

        # split on two-or-more spaces
        words = re.split(" {2,}", arg)

        status, value = BuiltIn().run_keyword_and_ignore_error(*words)
        print("result: {}\nstatus: {}".format(value, status))

    def do_where(self, arg):
        """
        Print the current robot stack (hierarchy of suites and tests,
        ending with the current keyword
        """
        prefix = "  "
        for i, x in enumerate(self.listener.stack):
            indent = prefix * i
            print("{}: {}-> {} ({})".format(i, indent, x.name, str(x)))
        print("")

    def do_locate_elements(self, arg):
        """Find and highlight all elements that match the given selenium locator

        Example:

            rdb> locate_elements //button[@title='Learn More']
        """
        try:
            elements = self.selenium.get_webelements(arg)
            print("Found {} matches".format(len(elements)))
            for element in elements:
                self._highlight_element(element)

        except Exception as e:
            print("dang.", e)

    def do_reset_elements(self, arg):
        """Remove highlighting added by `locate_elements`"""
        elements = self.selenium.get_webelements("//*[@data-original-style]")
        for element in elements:
            self._restore_element_style(element)

    def _highlight_element(self, element, style=None):
        """Highlight a Selenium Webdriver element

        style can be None, a string with css styles, or a dict of css styles
        element needs to be an instance of WebElement
        """

        if style is None:
            element_style = """
            box-shadow: 0px 1px 4px 2px inset #FFFF00;
            """
        elif isinstance(style, dict):
            element_style = "\n".join(
                "{}: {};".format(key, value) for key, value in style.items()
            )
        else:
            element_style = style

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
        # self.selenium.driver.execute_script(
        #     "arguments[0].setAttribute('data-original-style', arguments[0].getAttribute('style'));", element)
        # self.selenium.driver.execute_script(
        #     "arguments[0].setAttribute('style', arguments[1]);", element, new_style)

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
