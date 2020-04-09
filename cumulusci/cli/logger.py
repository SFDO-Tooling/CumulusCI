""" CLI logger """
import logging
import os
import sys
import requests
from pathlib import Path

import coloredlogs

from cumulusci.utils.__init__ import get_random_string

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
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if log_requests:
        requests.packages.urllib3.add_stderr_logger()


def get_tempfile_logger():
    """Creates a logger that writes to a temporary
    logfile. Returns the logger and path to tempfile"""
    logger = logging.getLogger("tempfile_logger")
    temp_logfile_dir = Path.home() / ".cumulusci" / "logs"
    temp_logfile_dir.mkdir(parents=True, exist_ok=True)

    filepath = temp_logfile_dir / f"{get_random_string(15)}.log"

    handler = logging.FileHandler(filepath, encoding="utf-8")
    handler.terminator = ""
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger, filepath
