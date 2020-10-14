import os
import re
import sys
import contextlib
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


@contextlib.contextmanager
def tee_stdout_stderr(args, logger, tempfile):
    """Tee stdout and stderr so that they're also routed to
    a log file. Add the current command arguments
    as the first item in the log."""
    real_stdout_write = sys.stdout.write
    real_stderr_write = sys.stderr.write

    # Add current command args as first line in logfile
    logger.debug(" ".join(args) + "\n")

    def stdout_write(s):
        output = strip_ansi_sequences(s)
        logger.debug(output)
        real_stdout_write(s)

    def stderr_write(s):
        output = strip_ansi_sequences(s)
        logger.debug(output)
        real_stderr_write(s)

    sys.stdout.write = stdout_write
    sys.stderr.write = stderr_write
    try:
        yield
    finally:
        # reset write functions
        sys.stdout.write = real_stdout_write
        sys.stderr.write = real_stderr_write

        # close temporary logfile
        logger.handlers[0].close()

        # log contents of tempfile to rotating log files
        with open(tempfile, "r", encoding="utf-8") as f:
            contents = f.read()

        logger = get_gist_logger()
        logger.debug(contents)
        # delete temporary log file
        os.remove(tempfile)


def get_gist_logger():
    """Determines the appropriate filepath for logfile
    and name for the logger. Returns a logger with
    RotatingFileHandler attached."""
    logfile_dir = Path.home() / ".cumulusci" / "logs"
    logfile_dir.mkdir(parents=True, exist_ok=True)
    logfile_path = logfile_dir / "cci.log"

    return get_rot_file_logger("stdout/stderr", logfile_path)


def get_rot_file_logger(name, path):
    """Returns a logger with a rotating file handler"""
    logger = logging.getLogger(name)

    handler = RotatingFileHandler(path, backupCount=5, encoding="utf-8")
    handler.doRollover()  # rollover existing log files
    handler.terminator = ""  # click.echo already adds a newline
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger


def strip_ansi_sequences(input):
    """Strip ANSI sequences from what's in buffer"""
    ansi_escape = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]")
    return ansi_escape.sub("", input)
