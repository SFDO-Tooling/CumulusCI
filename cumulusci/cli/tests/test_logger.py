from unittest.mock import patch
from pathlib import Path
from ..logger import init_logger, get_gist_logger, get_rot_file_logger


class TestLogger:
    @patch("cumulusci.cli.logger.requests")
    @patch("cumulusci.cli.logger.logging")
    def test_init_logger(self, logging, requests):
        init_logger(log_requests=True)
        requests.packages.urllib3.add_stderr_logger.assert_called_once()

    @patch("cumulusci.cli.logger.Path.mkdir")
    @patch("cumulusci.cli.logger.Path.home")
    @patch("cumulusci.cli.logger.get_rot_file_logger")
    def test_get_gist_logger(self, file_logger, home, mkdir):
        home.return_value = Path("/Users/bob.ross")
        get_gist_logger()
        file_logger.assert_called_once_with(
            "stdout/stderr", Path("/Users/bob.ross/.cumulusci/logs/cci.log")
        )

    @patch("cumulusci.cli.logger.RotatingFileHandler")
    @patch("cumulusci.cli.logger.logging")
    def test_get_rot_file_logger(self, logging, rot_filehandler):

        logger_name = "The happy logger"
        path = "happy/logger/path"
        logger = get_rot_file_logger(logger_name, path)

        logging.getLogger.assert_called_once_with(logger_name)
        rot_filehandler.assert_called_once_with(path, backupCount=5, encoding="utf-8")
        logger.addHandler.assert_called_once()
        logger.setLevel.assert_called_once()
