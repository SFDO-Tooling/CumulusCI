""" Utilities for testing CumulusCI

MockLoggingHandler: a logging handler that we can assert"""
from __future__ import unicode_literals

import logging


class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs.

    Messages are available from an instance's ``messages`` dict, in order,
    indexed by a lowercase log level string (e.g., 'debug', 'info', etc.).
    """

    def __init__(self, *args, **kwargs):
        self.messages = {'debug': [], 'info': [], 'warning': [], 'error': [],
                         'critical': []}
        super(MockLoggingHandler, self).__init__(*args, **kwargs)

    def emit(self, record):
        "Store a message from ``record`` in the instance's ``messages`` dict."
        self.acquire()
        try:
            self.messages[record.levelname.lower()].append(record.getMessage())
        finally:
            self.release()

    def reset(self):
        """ Reset the handler in TestCase.setUp() to clear the msg list """
        self.acquire()
        try:
            for message_list in list(self.messages.values()):
                del message_list[:]
        finally:
            self.release()
