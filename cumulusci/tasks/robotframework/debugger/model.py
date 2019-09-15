import os
import re
import fnmatch


class Base:
    """Base class for keywords, testcases, and suites

    This is mainly used to store the data passed to use from the
    listener methods.
    """

    def __init__(self, name, attrs):
        self.name = name
        self.attrs = attrs

    def __str__(self):
        return "<{}: {}>".format(self.__class__.__name__, self.name)

    @property
    def longname(self):
        # Robot's a bit inconsistent here: suites and test cases have
        # a longname attribute, for the keyword the name is the longname.
        if "longname" in self.attrs:
            return self.attrs["longname"]
        else:
            return self.name


class Testcase(Base):
    pass


class Keyword(Base):
    # should this be __repr__?
    def __str__(self):
        return "  ".join([self.name] + self.attrs["args"])


class Suite(Base):
    # should this be __repr__?
    def __str__(self):
        path = self.attrs["source"]
        rel_path = os.path.relpath(path)
        if not rel_path.startswith("."):
            rel_path = "./" + rel_path
        return "<{}: {}>".format(self.__class__.__name__, rel_path)


class Breakpoint:
    """A breakpoint

    :param breakpoint_type:  class of object to break on;
                             currently only Keyword is supported.
                             Eventually I want to support setting breakpoints
                             when a suite or test case is first started, before
                             any keywords run.
    :param pattern:          glob-style pattern to match against
                             the current step
    :param temporary:        if True, the breakpoint is removed once
                             it triggers. Used for setting temporary
                             breakpoints for stepping through the code

    Note: when a breakpoint is encountered, a string will be formed
    with the fully qualified name of the current testcase and the
    fully qualified name of the current keyword, separated with "::"

    The breakpoint pattern will be matched against this string.

    Example:
        Root_suite.sub_suite.a test case::BuiltIn.log

    To break on the "Salesforce.breakpoint" keyword in any test, the
    breakpoint could use any one of these patterns depending on how
    precise you want to be:

        - *::cumulusci.robotframework.Salesforce.Breakpoint
        - *::*.Breakpoint
        - *.Breakpoint

    """

    def __init__(self, breakpoint_type, pattern, temporary=False):
        self.breakpoint_type = breakpoint_type
        self.pattern = fnmatch.translate(pattern)
        self.temporary = temporary

    # this was useful in an earlier version of the code; now
    # I'm not sure it's needed anymore.
    # def __eq__(self, other):
    #     """Breakpoints are equal if all of their attributes are equal"""
    #     return (
    #         self.breakpoint_type == other.breakpoint_type
    #         and self.pattern == other.pattern
    #         and self.temporary == other.temporary
    #     )

    def match(self, context):
        """Return True if the breakpoint matches the current context"""
        if re.match(self.pattern, context, re.IGNORECASE):
            return True
        return False
