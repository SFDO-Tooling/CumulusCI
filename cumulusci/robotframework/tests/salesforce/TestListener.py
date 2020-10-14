"""This hybrid library/listener can be used to verify messages that
    have been logged and keywords have been called.

    This works by listening for log messages and keywords via the
    listener interface, and saving them in a cache. Keywords are
    provided for doing assertions on called keywords and for resetting
    the cache.

    The keyword cache is reset for each test case to help keep it
    from growing too large.

"""
import re


class TestListener(object):
    __test__ = False  # this class should be ignored by pytest
    ROBOT_LIBRARY_SCOPE = "TEST SUITE"
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self):
        self.ROBOT_LIBRARY_LISTENER = self
        self.message_log = []
        self.keyword_log = []
        self.message_logging_enabled = True

    def _log_message(self, message):
        """Called whenever a message is added to the log"""
        if self.message_logging_enabled:
            self.message_log.append(message)

    def _start_test(self, name, attrs):
        self.reset_test_listener_keyword_log()

    def _end_keyword(self, name, attrs):
        attrs_subset = {name: attrs[name] for name in ("status", "args")}
        self.keyword_log.append((name, attrs_subset))

    def reset_test_listener_keyword_log(self):
        """Reset the keyword cache

        This can be used to reset the cache in the middle of a
        testcase so that the 'Assert keyword Status' keyword will only
        apply to keywords called from this point onwards.

        """
        self.keyword_log.clear()

    def reset_test_listener_message_log(self):
        self.message_log = []

    def assert_keyword_status(self, expected_status, keyword_name, *args):
        """Assert that all keyword with the given name and args have the given status

        Keyword names need to be passed in as fully qualified names
        exactly as they appear in the logs.

        expected_status should be either PASS or FAIL

        Example
            Log  Hello, world
            Assert keyword status  PASS  BuiltIn.log  Hello, world

        """

        keyword_was_found = False
        for name, attrs in self.keyword_log:
            if name == keyword_name and args == tuple(attrs["args"]):
                keyword_was_found = True
                if attrs["status"] != expected_status:
                    message = (
                        f"Status of keyword {keyword_name} with args {args} "
                        f"expected to be {expected_status} but was {attrs['status']}"
                    )
                    raise AssertionError(message)
        if not keyword_was_found:
            raise AssertionError(
                f"No keyword with name '{keyword_name}' with args '{args}' was found"
            )

    def assert_robot_log(self, message_pattern, log_level=None):
        """Assert that a message matching the regex pattern was emitted"""
        for message in self.message_log:
            # note: message is a dictionary with the following keys:
            # 'timestamp', 'message', 'level', 'html'
            if re.search(message_pattern, message["message"], re.MULTILINE):
                if log_level is None or message["level"] == log_level:
                    return True
        raise AssertionError(
            "Could not find a robot log message matching the pattern '{}'".format(
                message_pattern
            )
        )
