""" CLI logger """
import logging
import os
import sys
import tempfile
import requests
from contextlib import contextmanager, ExitStack

import coloredlogs

try:
    import colorama
except ImportError:
    # coloredlogs only installs colorama on Windows
    pass


@contextmanager
def init_logger(log_requests=False):
    """ Context manager that initializes the logger """
    with ExitStack() as onexit:
        logger = logging.getLogger(__name__.split(".")[0])
        old_handlers = logger.handlers.copy()
        for old_handler in old_handlers:  # pragma: no cover
            logger.removeHandler(old_handler)
            onexit.callback(lambda handler=old_handler: logger.addHandler(handler))

        if os.name == "nt" and "colorama" in sys.modules:  # pragma: no cover
            colorama.init()
            onexit.callback(colorama.deinit)

        formatter = coloredlogs.ColoredFormatter(fmt="%(asctime)s: %(message)s")
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        onexit.callback(lambda: logger.removeHandler(handler))
        effective_level = logger.getEffectiveLevel()
        logger.setLevel(logging.DEBUG)
        onexit.callback(lambda: logger.setLevel(effective_level))

        old_propagate = logger.propagate
        logger.propagate = False

        onexit.callback(lambda: setattr(logger, "propagate", old_propagate))

        if log_requests:
            requests_handler = requests.packages.urllib3.add_stderr_logger()

            onexit.callback(
                lambda: logging.getLogger("urllib3").removeHandler(requests_handler)
            )
        yield


def get_tempfile_logger():
    """Creates a logger that writes to a temporary
    logfile. Returns the logger and path to tempfile"""
    logger = logging.getLogger("tempfile_logger")
    file_handle, filepath = tempfile.mkstemp()
    # close the file as it will be opened again by FileHandler
    os.close(file_handle)
    handler = logging.FileHandler(filepath, encoding="utf-8")
    handler.terminator = ""
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger, filepath
