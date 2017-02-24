""" Utilities for CumulusCI Core

import_class: Task class defn import helper
MockLoggingHandler: a handler for testing logging """

import logging


def import_class(path):
    """ Import a class from a string module class path """
    components = path.split('.')
    module = components[:-1]
    module = '.'.join(module)
    mod = __import__(module, fromlist=[components[-1]])
    return getattr(mod, components[-1])


class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs."""

    def __init__(self, *args, **kwargs):
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def reset(self):
        """ Reset the handler for each test """
        self.messages = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': [],
        }
