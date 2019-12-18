from unittest.mock import patch
from ..logger import init_logger, get_gist_logger, get_rot_file_logger


class TestLogger:
    @patch("cumulusci.cli.logger.requests")
    @patch("cumulusci.cli.logger.logging")
    def test_init_logger(self, logging, requests):
        init_logger(log_requests=True)
        requests.packages.urllib3.add_stderr_logger.assert_called_once()

    @patch("cumulusci.cli.logger.get_rot_file_logger")
    def test_get_gist_logger(self, file_logger):
        repo_root = "path/to/repo/root"
        get_gist_logger(repo_root)
        file_logger.assert_called_once_with("sys.stdout", f"{repo_root}/.cci/cci.log")

    @patch("cumulusci.cli.logger.get_rot_file_logger")
    def test_get_gist_logger__no_repo_root(self, file_logger):
        get_gist_logger(None)
        file_logger.assert_called_once_with("sys.stdout", "cci.log")

    @patch("cumulusci.cli.logger.logging")
    def test_get_rot_file_logger(self, logging):
        logger_name = "The happy logger"
        logfile_path = "happy/logger/path"
        logger = get_rot_file_logger(logger_name, logfile_path)

        logging.getLogger.assert_called_once_with(logger_name)
        logging.handlers.RotatingFileHandler.assert_called_once_with(
            logfile_path, backupCount=5
        )
        logger.addHandler.assert_called_once()
        logger.setLevel.assert_called_once()
