import datetime
import unittest

import pytz

from .. import utils

from collections import OrderedDict
from cumulusci.core.exceptions import ConfigMergeError


class TestUtils(unittest.TestCase):
    def test_parse_datetime(self):
        dt = utils.parse_datetime("2018-07-30", "%Y-%m-%d")
        self.assertEqual(dt, datetime.datetime(2018, 7, 30, 0, 0, 0, 0, pytz.UTC))

    def test_process_bool_arg(self):
        for arg in (True, "True", "true", "1"):
            self.assertTrue(utils.process_bool_arg(arg))

        for arg in (False, "False", "false", "0"):
            self.assertFalse(utils.process_bool_arg(arg))

        for arg in (None, datetime.datetime.now()):
            self.assertIsNone(utils.process_bool_arg(arg))

    def test_process_list_arg(self):
        self.assertEqual([1, 2], utils.process_list_arg([1, 2]))
        self.assertEqual(["a", "b"], utils.process_list_arg("a, b"))
        self.assertEqual(None, utils.process_list_arg(None))

    def test_decode_to_unicode(self):
        self.assertEqual(u"\xfc", utils.decode_to_unicode(b"\xfc"))
        self.assertEqual(u"\u2603", utils.decode_to_unicode(u"\u2603"))
        self.assertEqual(None, utils.decode_to_unicode(None))


class TestMergedConfig(unittest.TestCase):
    def test_init(self):
        config = utils.merge_config(
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
            config = utils.merge_config(
                OrderedDict(
                    [
                        ("user_config", {"hello": "christian", "test": [1, 2]}),
                        ("global_config", {"hello": "world", "test": {"sample": 1}}),
                    ]
                )
            )
        exception = cm.exception
        self.assertEqual(exception.config_name, "user_config")
