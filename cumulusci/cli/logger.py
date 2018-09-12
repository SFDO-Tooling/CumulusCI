""" CLI logger """
from __future__ import unicode_literals

import logging

import coloredlogs


def init_logger():
    """ Initialize the logger """

    formatter = coloredlogs.ColoredFormatter(fmt="%(asctime)s: %(message)s")

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    logger = logging.getLogger(__name__.split(".")[0])
    for handler in logger.handlers:  # pragma: nocover
        logger.removeHandler(handler)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
