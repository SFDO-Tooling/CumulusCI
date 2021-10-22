""" CLI logger """
import logging
import os
import sys
import tempfile

import coloredlogs  # noqa: F401
import requests
from rich.logging import RichHandler

try:
    import colorama
except ImportError:
    # coloredlogs only installs colorama on Windows
    pass


def init_logger(debug=False):
    """Initialize the logger"""

    logger = logging.getLogger(__name__.split(".")[0])
    for handler in logger.handlers:  # pragma: no cover
        logger.removeHandler(handler)

    if os.name == "nt" and "colorama" in sys.modules:  # pragma: no cover
        colorama.init()

    logger.addHandler(
        RichHandler(
            show_level=debug,
            show_path=debug,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
    )
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if debug:
        requests.packages.urllib3.add_stderr_logger()


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
