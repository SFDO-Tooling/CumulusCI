import logging
import os
from unittest.mock import Mock, patch

from ..logger import get_tempfile_logger, init_logger


class TestLogger:
    @patch("cumulusci.cli.logger.requests")
    @patch("cumulusci.cli.logger.logging")
    def test_init_logger(self, logging, requests):
        logger = Mock(handlers=["leftover"])
        logging.getLogger.return_value = logger
        init_logger()
        logger.removeHandler.assert_called_once_with("leftover")
        logger.addHandler.assert_called_once()

    def test_get_tempfile_logger(self):
        logger, tempfile = get_tempfile_logger()
        assert os.path.isfile(tempfile)
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.FileHandler)
        # delete temp logfile
        logger.handlers[0].close()
        os.remove(tempfile)
