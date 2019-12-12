import io
import sys
from unittest.mock import patch
from ..logger import init_logger

from cumulusci.cli.logger import LogStream


class TestLogger:
    @patch("cumulusci.cli.logger.requests")
    @patch("cumulusci.cli.logger.logging")
    def test_init_logger(self, logging, requests):
        init_logger(log_requests=True)
        requests.packages.urllib3.add_stderr_logger.assert_called_once()


class TestLogStream:
    def test_logstream(self):
        sys.stdout = LogStream(sys.stdout, io.StringIO())

        expected_log_content = "Hello there!"
        sys.stdout.write(expected_log_content)

        log_content = sys.stdout.read_log()
        assert log_content == expected_log_content
