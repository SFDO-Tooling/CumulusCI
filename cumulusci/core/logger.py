import logging
import os
import tempfile
import coloredlogs

def init_logger():
    """ Initializes self.logger """
    logger = logging.getLogger('cumulusci')
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = coloredlogs.ColoredFormatter(
        fmt='%(asctime)s: %(message)s'
    )

    # Create the log_content handler
    log_file = tempfile.mkstemp()[1]
    log_content_handler = logging.FileHandler(log_file)
    log_content_handler.setLevel(logging.DEBUG)
    log_content_handler.setFormatter(formatter)
    logger.addHandler(log_content_handler)

    # Create the stdout handler
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
        
    return logger, log_file

def delete_log(log_file):
    os.remove(log_file)

logger, log_file = init_logger()
