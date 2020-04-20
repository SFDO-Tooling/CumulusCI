import os
import logging

from unittest.mock import patch
from ..logger import init_logger, get_tempfile_logger


class TestLogger:
    @patch("cumulusci.cli.logger.requests")
    @patch("cumulusci.cli.logger.logging")
    def test_init_logger(self, logging, requests):
        init_logger(log_requests=True)
        requests.packages.urllib3.add_stderr_logger.assert_called_once()

    def test_get_tempfile_logger(self):
        logger, tempfile = get_tempfile_logger()
        assert os.path.isfile(tempfile)
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)
        # delete temp logfile
        logger.handlers[0].close()
        os.remove(tempfile)
