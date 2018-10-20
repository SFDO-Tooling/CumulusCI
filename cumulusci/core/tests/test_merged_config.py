import unittest

from cumulusci.core.config import MergedConfig


class TestMergedConfig(unittest.TestCase):
    def test_init(self):
        config = MergedConfig(
            user_config={"hello": "christian"}, global_config={"hello": "world"}
        )
        self.assertEqual(config.hello, "christian")
