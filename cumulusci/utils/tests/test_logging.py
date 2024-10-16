import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

from cumulusci.utils.logging import (
    get_gist_logger,
    get_rot_file_logger,
    strip_ansi_sequences,
    tee_stdout_stderr,
)


class TestUtilLogging:
    @patch("cumulusci.utils.logging.get_gist_logger")
    def test_tee_stdout_stderr(self, gist_logger):
        args = ["cci", "test"]
        logger = Mock(handlers=[Mock()])
        gist_logger.return_value = Mock()
        # Setup temp logfile
        tempfile = "tempfile.log"
        log_content = "This is the content for the temp log file. And '┌' is an annoying character for Windows."
        with open(tempfile, "w", encoding="utf-8") as f:
            f.write(log_content)

        expected_stdout_text = "This is expected stdout.\n"
        expected_stderr_text = "This is expected stderr.\n"
        with tee_stdout_stderr(args, logger, tempfile):
            sys.stdout.write(expected_stdout_text)
            sys.stderr.write(expected_stderr_text)

        gist_logger.assert_called_once()
        assert logger.debug.call_count == 3
        assert logger.debug.call_args_list[0][0][0] == "cci test\n"
        assert logger.debug.call_args_list[1][0][0] == expected_stdout_text
        assert logger.debug.call_args_list[2][0][0] == expected_stderr_text
        # temp log file should be deleted
        assert not os.path.isfile(tempfile)

    @patch("cumulusci.utils.logging.Path.mkdir")
    @patch("cumulusci.utils.logging.Path.home")
    @patch("cumulusci.utils.logging.get_rot_file_logger")
    def test_get_gist_logger(self, file_logger, home, mkdir):
        home.return_value = Path("/Users/bob.ross")
        get_gist_logger()
        file_logger.assert_called_once_with(
            "stdout/stderr", Path("/Users/bob.ross/.cumulusci/logs/cci.log")
        )

    @patch("cumulusci.utils.logging.RotatingFileHandler")
    @patch("cumulusci.utils.logging.logging")
    def test_get_rot_file_logger(self, logging, rot_filehandler):
        logger_name = "The happy logger"
        path = "happy/logger/path"
        logger = get_rot_file_logger(logger_name, path)

        logging.getLogger.assert_called_once_with(logger_name)
        rot_filehandler.assert_called_once_with(path, backupCount=5, encoding="utf-8")
        logger.addHandler.assert_called_once()
        logger.setLevel.assert_called_once()

    def test_strip_ansi_sequences(self):
        ansi_str = "\033[31mGoodbye ANSI color sequences!\033[0m"
        plain_str = "This is [just a plain old string with some] [symbols]"

        ansi_string_result = strip_ansi_sequences(ansi_str)
        plain_string_result = strip_ansi_sequences(plain_str)

        assert ansi_string_result == "Goodbye ANSI color sequences!"
        assert plain_string_result == plain_str
