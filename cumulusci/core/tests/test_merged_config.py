import unittest
from collections import OrderedDict

from cumulusci.core.merge import merge_config
from cumulusci.core.exceptions import ConfigMergeError


class TestMergedConfig(unittest.TestCase):
    def test_init(self):
        config = merge_config(
            OrderedDict(
                [
                    ("user_config", {"hello": "christian"}),
                    ("global_config", {"hello": "world"}),
                ]
            )
        )
        self.assertEqual(config["hello"], "christian")

    def test_merge_failure(self):
        with self.assertRaises(ConfigMergeError) as cm:
            config = merge_config(
                OrderedDict(
                    [
                        ("user_config", {"hello": "christian", "test": [1, 2]}),
                        ("global_config", {"hello": "world", "test": {"sample": 1}}),
                    ]
                )
            )
        exception = cm.exception
        self.assertEqual(exception.config_name, "user_config")
