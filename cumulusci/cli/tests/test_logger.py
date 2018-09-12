import mock
import unittest

from ..logger import init_logger


class TestLogger(unittest.TestCase):
    @mock.patch("cumulusci.cli.logger.logging")
    def test_init_logger(self, logging):
        init_logger()
