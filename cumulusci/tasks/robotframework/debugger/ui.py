import cmd
import os
import pdb
import re
import signal
import sys
import textwrap

from robot.libraries.BuiltIn import BuiltIn

from cumulusci.cli.ui import CliTable

# this is code we use to inject a style into the DOM
initialize_highlight_js = """
    if (!window.rdbInitialized) {
        console.log("initializing rdb...");
        window.rdbInitialized = true;
        var new_style = document.createElement('style');
        new_style.type = 'text/css';
        new_style.innerHTML = '.rdbHighlight {box-shadow: 0px 1px 4px 2px inset #FFFF00}';
        document.getElementsByTagName('head')[0].appendChild(new_style);
    };
"""


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
    def webbrowser(self):
        # This is a property because we can't initialize it until we
        # need it. We'll reinitialize it every time it's used. It's
        # fast enough, and this way it should work even if the user
        # is testing a suite with some playwright and some selenium
        # tests
        libraries = self.builtin.get_library_instance(all=True)
        if "SeleniumLibrary" in libraries:
            return SeleniumProxy(libraries["SeleniumLibrary"])
        elif "Browser" in libraries:
            return BrowserProxy(libraries["Browser"])
        return None

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
        """Find and highlight all elements that match the given locator

        Example:

            rdb> locate_elements  //button[@title='Learn More']
        """
        try:
            self.webbrowser.highlight_elements(locator)
        except Exception as e:
            print(f"Unable to highlight elements: {e}")

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
        try:
            self.webbrowser.restore_element_style()
        except Exception as e:
            print(f"Unable to reset element styles: {e}")

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


class SeleniumProxy:
    """Proxy for performing debug operations in a Selenium browser"""

    def __init__(self, library_instance):
        self.selenium = library_instance

    def highlight_elements(self, locator):
        """Highlights Selenium Webdriver elements that match a locator"""
        self.selenium.driver.execute_script(initialize_highlight_js)

        elements = self.selenium.get_webelements(locator)
        for element in elements:
            self.selenium.driver.execute_script(
                "arguments[0].classList.add('rdbHighlight');", element
            )
        print(f"{len(elements)} elements found")

    def restore_element_style(self):
        """Remove the style added by `highlight_elements`"""
        for element in self.selenium.get_webelements("css:.rdbHighlight"):
            self.selenium.driver.execute_script(
                "arguments[0].classList.remove('rdbHighlight')", element
            )


class BrowserProxy:
    """Proxy for performing debug operations in a Playwright browser"""

    def __init__(self, library_instance):
        self.browser = library_instance

    def highlight_elements(self, selector):
        """Highlight one or more elements by applying a custom css class"""
        init_script = f"() => {{{initialize_highlight_js}}};"
        self.browser.evaluate_javascript(None, init_script)

        elements = self.browser.get_elements(selector)
        if elements:
            self.browser.evaluate_javascript(
                selector,
                """(elements) => {
                    for (element of elements) {
                        element.classList.add('rdbHighlight')
                    }
                }""",
                all_elements=True,
            )
        print(f"{len(elements)} elements found")

    def restore_element_style(self):
        """Remove the style added by `highlight_elements`"""
        self.browser.evaluate_javascript(
            ".rdbHighlight",
            """(elements) => {
                for (element of elements) {
                    element.classList.remove('rdbHighlight')
                }
            }""",
            all_elements=True,
        )
