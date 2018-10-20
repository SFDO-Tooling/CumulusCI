import unittest

from cumulusci.core.config import MergedConfig
from cumulusci.core.exceptions import ConfigMergeError


class TestMergedConfig(unittest.TestCase):
    def test_init(self):
        config = MergedConfig(
            user_config={"hello": "christian"}, global_config={"hello": "world"}
        )
        self.assertEqual(config.hello, "christian")

    def test_merge_failure(self):
        with self.assertRaises(ConfigMergeError) as cm:
            config = MergedConfig(
                user_config={"hello": "christian", "test": [1, 2]},
                global_config={"hello": "world", "test": {"sample": 1}},
            )
        exception = cm.exception
        self.assertEqual(exception.filename, "user_config")
