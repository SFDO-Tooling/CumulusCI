"""
Robot Debugger

"""

from cumulusci.tasks.robotframework.debugger import (
    Breakpoint,
    DebuggerCli,
    Keyword,
    Suite,
    Testcase,
)


class DebugListener(object):
    """A robot framework listener for debugging test cases

    This acts as the controller for the debugger. It is responsible
    for managing breakpoints, and pausing execution of a test when a
    breakpoint is hit.

    The listener is also responsible for instantiating the debugger UI
    (class DebuggerCli).

    """

    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, *breakpoints):
        self.show_initial_help = True
        self.current_file = None
        self.stack = []
        self.rdb = DebuggerCli(listener=self)
        if breakpoints:
            self.breakpoints = list(breakpoints)
        else:
            self.breakpoints = [
                Breakpoint(Keyword, "*::cumulusci.robotframework.*.Breakpoint"),
            ]

    def start_suite(self, name, attrs):
        self.stack.append(Suite(name, attrs))

    def start_test(self, name, attrs):
        self.stack.append(Testcase(name, attrs))

    def start_keyword(self, name, attrs):
        context = Keyword(name, attrs)
        self.stack.append(context)
        self.break_if_breakpoint()

    def end_keyword(self, name, attrs):
        self.stack.pop()

    def end_test(self, name, attrs):
        self.stack.pop()

    def end_suite(self, name, attrs):
        self.stack.pop()

    def do_step(self):
        """Single-step through the code

        This will set a temporary breakpoint on the next keyword in
        the current context before continuing. Once the breakpoint
        is hit, it will be removed from the list of breakpoints.
        """
        breakpoint = Breakpoint(
            Keyword, "{}::*".format(self.stack[-2].longname), temporary=True
        )
        self.breakpoints.append(breakpoint)

    def break_if_breakpoint(self):
        """Pause test execution and issue a prompt if we are at a breakpoint"""

        # filter breakpoints to only those that match the current context
        # (eg: Suite, Testcase, Keyword), and iterate over them looking
        # for a match.
        for breakpoint in [
            bp
            for bp in self.breakpoints
            if isinstance(self.stack[-1], bp.breakpoint_type)
        ]:
            statement = "{}::{}".format(self.stack[-2].longname, self.stack[-1].name)
            if breakpoint.match(statement):
                if breakpoint.temporary:
                    self.breakpoints.remove(breakpoint)

                intro = "\n"
                if self.show_initial_help:
                    self.show_initial_help = False
                    intro += self.rdb.intro
                intro += "\n> {}\n-> {}".format(
                    self.stack[-2].longname, str(self.stack[-1])
                )

                # Note: this call won't return until a debugger command
                # has been issued which returns True (eg: 'continue' or 'step')
                self.rdb.cmdloop(intro)
                return
