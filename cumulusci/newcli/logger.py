""" CLI logger """

import logging

import coloredlogs


def init_logger():
    """ Initialize the logger """

    formatter = coloredlogs.ColoredFormatter(fmt='%(asctime)s: %(message)s')

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    logger = logging.getLogger(__name__.split('.')[0])
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False
