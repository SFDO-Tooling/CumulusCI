"""
    This hybrid library/listener can be used to verify
    messages that have been logged.

    This works by listening for log messages via the listener
    interface, and saving them in a cache. Keywords are provided
    for searching the cache, and for resetting the cache.
"""
from robot.libraries.BuiltIn import BuiltIn
import re


class TestListener(object):
    ROBOT_LIBRARY_SCOPE = "TEST SUITE"
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self):
        self.ROBOT_LIBRARY_LISTENER = self
        self.log_messages = []
        self.capture_log = True

    def _log_message(self, message):
        """Called whenever a message is added to the log"""
        if self.capture_log:
            self.log_messages.append(message)

    def reset_robot_log_cache(self):
        self.log_messages = []

    def assert_robot_log(self, message_pattern, log_level=None):
        """Assert that a message matching the pattern was emitted"""
        BuiltIn().log_to_console("\n")
        for message in self.log_messages:
            # note: message is a dictionary with the following keys:
            # 'timestamp', 'message', 'level', 'html'
            if re.search(message_pattern, message["message"], re.MULTILINE):
                if log_level is None or message["level"] == log_level:
                    return True
        raise Exception(
            "Could not find a robot log message matching the pattern '{}'".format(
                message_pattern
            )
        )
