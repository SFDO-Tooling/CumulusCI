import mock
import unittest

from ..logger import init_logger


class TestLogger(unittest.TestCase):
    @mock.patch("cumulusci.cli.logger.requests")
    @mock.patch("cumulusci.cli.logger.logging")
    def test_init_logger(self, logging, requests):
        init_logger(log_requests=True)
        requests.packages.urllib3.add_stderr_logger.assert_called_once()
