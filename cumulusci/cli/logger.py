""" CLI logger """
import logging
import logging.handlers
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
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if log_requests:
        requests.packages.urllib3.add_stderr_logger()


def get_gist_logger(repo_root):
    """Determines the appropriate filepath for logfile
    and name for the logger. Returns a logger with
    RotatingFileHandler attached."""
    if repo_root:
        logfile_path = "~/.cumulusci/logs/cci.log"
        # create .cumulusic/logs if it doesn't exist
        os.makedirs(os.path.dirname(logfile_path), exist_ok=True)
    else:
        logfile_path = "cci.log"
    return get_rot_file_logger("sys.stdout", logfile_path)


def get_rot_file_logger(name, path):
    """Returns a logger with a rotating file handler"""
    logger = logging.getLogger(name)

    handler = logging.handlers.RotatingFileHandler(path, backupCount=5)
    handler.doRollover()  # rollover existing log files
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
