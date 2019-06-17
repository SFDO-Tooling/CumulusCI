""" CLI logger """
from __future__ import unicode_literals

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
    for handler in logger.handlers:  # pragma: nocover
        logger.removeHandler(handler)

    if os.name == "nt" and "colorama" in sys.modules:  # pragma: nocover
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
