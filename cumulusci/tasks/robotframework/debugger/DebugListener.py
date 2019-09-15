"""
Robot Debugger

"""

from cumulusci.tasks.robotframework.debugger import DebuggerCli
from cumulusci.tasks.robotframework.debugger import Breakpoint, Suite, Testcase, Keyword


class DebugListener(object):
    """A robot framework listener for debugging test cases

    This acts as the controller for the debugger. It is responsible for
    managing breakpoints.

    Note to self: in Breakpoint.match, "context" refers to testcase::keyword combination

    """

    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, *breakpoints):
        self.current_file = None
        self.stack = []
        self.rdb = DebuggerCli(listener=self)
        if breakpoints:
            self.breakpoints = breakpoints
        else:
            self.breakpoints = [
                Breakpoint(Keyword, "*::cumulusci.robotframework.Salesforce.Breakpoint")
            ]

    def start_suite(self, name, attrs):
        self.stack.append(Suite(name, attrs))

    def start_test(self, name, attrs):
        self.stack.append(Testcase(name, attrs))

    def _break_if_breakpoint(self):
        for breakpoint in [
            bp
            for bp in self.breakpoints
            if isinstance(self.stack[-1], bp.breakpoint_type)
        ]:
            statement = "{}::{}".format(self.stack[-2].longname, self.stack[-1].name)
            if breakpoint.match(statement):
                if breakpoint.temporary:
                    self.breakpoints.remove(breakpoint)

                self.rdb.cmdloop(
                    "\n> {}\n-> {}".format(self.stack[-2].longname, str(self.stack[-1]))
                )
                return

    def start_keyword(self, name, attrs):
        # at this point, context might be ['suite', 'subsuite', 'testcase']

        context = Keyword(name, attrs)
        self.stack.append(context)
        self._break_if_breakpoint()

    def end_keyword(self, name, attrs):
        self.stack.pop()

    def end_test(self, name, attrs):
        self.stack.pop()

    def end_suite(self, name, attrs):
        self.stack.pop()

    def do_step(self):
        """Single-step through the code

        This will set a breakpoint on the next keyword in
        the current context before continuing
        """
        # create new breakpoint on the next keyword in the parent of
        # the current context
        breakpoint = Breakpoint(
            Keyword, "{}::*".format(self.stack[-2].longname), temporary=True
        )
        self.breakpoints.append(breakpoint)

    def add_breakpoint(self, breakpoint_type, pattern, temporary=False):
        """Add a breakpoint

        Pattern is a glob-style pattern (eg: *.breakpoint). If temporary
        is True, the breakpoint will be automatically removed once it
        has been encountered.
        """
        breakpoint = Breakpoint(breakpoint_type, pattern, temporary)
        if breakpoint not in self.breakpoints:
            self.breakpoints.append(breakpoint)
