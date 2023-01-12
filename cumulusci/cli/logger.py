""" CLI logger """
import logging
import os
import sys
import tempfile

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
            rich_tracebacks=True,
            show_level=debug,
            show_path=debug,
            tracebacks_show_locals=debug,
        )
    )
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if debug:  # pragma: no cover
        # Referenced from:
        # https://github.com/urllib3/urllib3/blob/cd55f2fe98df4d499ab5c826433ee4995d3f6a60/src/urllib3/__init__.py#L48
        def add_rich_logger(
            module: str, level: int = logging.DEBUG
        ) -> logging.StreamHandler:
            """Retrieve the logger for the given module.
            Remove all handlers from it, and add a single RichHandler."""
            logger = logging.getLogger(module)
            for handler in logger.handlers:
                logger.removeHandler(handler)

            handler = RichHandler()
            logger.addHandler(handler)
            logger.setLevel(level)
            logger.debug(f"Added rich.logging.RichHandler to logger: {module}")
            return handler

        # monkey patch urllib3 logger
        requests.packages.urllib3.add_stderr_logger = add_rich_logger
        requests.packages.urllib3.add_stderr_logger("urllib3")


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
