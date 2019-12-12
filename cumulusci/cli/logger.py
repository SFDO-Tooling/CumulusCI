""" CLI logger """
import logging
import os
import sys

import requests

import coloredlogs

try:
    import colorama
except ImportError:
    # coloredlogs only installs colorama on Windows
    pass


def init_logger(log_requests=False):
    """ Initialize the logger """

    logger = logging.getLogger(__name__.split(".")[0])
    for handler in logger.handlers:  # pragma: no cover
        logger.removeHandler(handler)

    if os.name == "nt" and "colorama" in sys.modules:  # pragma: no cover
        colorama.init()

    formatter = coloredlogs.ColoredFormatter(fmt="%(asctime)s: %(message)s")
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if log_requests:
        requests.packages.urllib3.add_stderr_logger()


class LogStream:
    """Logs all input to a stream in a buffer, which can
    be read from. All data passed to the stream's `write()`
    is passed directly throurgh. This is how we capture everything
    from stdout to create a gist (if the user chooses to).

    Usage with stdout:
        sys.stdout = LogStream(sys.stdout, io.StringIO())
    """

    def __init__(self, stream, buffer):
        self.stream = stream
        self.log = buffer

    def write(self, data):
        self.log.write(data)
        self.stream.write(data)
        self.flush()

    def flush(self):
        """Needed incase there are references to sys.stdout.flush()"""
        self.stream.flush()

    def read_log(self):
        """Returns the contents of buffer, then flushes buffer"""
        self.log.seek(0)
        contents = self.log.read()
        self.log.flush()
        return contents
