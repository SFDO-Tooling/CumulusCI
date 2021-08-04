import datetime
import os
import re
import unittest

import pytest
import pytz

from cumulusci.core.exceptions import ConfigMergeError, TaskOptionsError
from cumulusci.utils import temporary_dir, touch

from .. import utils


class TestUtils(unittest.TestCase):
    def test_parse_datetime(self):
        dt = utils.parse_datetime("2018-07-30", "%Y-%m-%d")
        self.assertEqual(dt, datetime.datetime(2018, 7, 30, 0, 0, 0, 0, pytz.UTC))

    def test_process_bool_arg(self):
        for arg in (True, "True", "true", "1"):
            self.assertTrue(utils.process_bool_arg(arg))

        for arg in (False, "False", "false", "0"):
            self.assertFalse(utils.process_bool_arg(arg))

        import warnings

        with warnings.catch_warnings(record=True):
            assert utils.process_bool_arg(None) is False

        with pytest.raises(TypeError):
            utils.process_bool_arg(datetime.datetime.now())

        with pytest.raises(TypeError):
            utils.process_bool_arg("xyzzy")

    def test_process_list_arg(self):
        self.assertEqual([1, 2], utils.process_list_arg([1, 2]))
        self.assertEqual(["a", "b"], utils.process_list_arg("a, b"))
        self.assertEqual(None, utils.process_list_arg(None))

    def test_process_glob_list_arg(self):
        with temporary_dir():
            touch("foo.py")
            touch("bar.robot")

            # Expect passing arg as list works.
            self.assertEqual(
                ["foo.py", "bar.robot"],
                utils.process_glob_list_arg(["foo.py", "bar.robot"]),
            )

            # Falsy arg should return an empty list
            self.assertEqual([], utils.process_glob_list_arg(None))
            self.assertEqual([], utils.process_glob_list_arg(""))
            self.assertEqual([], utils.process_glob_list_arg([]))

            # Expect output to be in order given
            self.assertEqual(
                ["foo.py", "bar.robot"],
                utils.process_glob_list_arg("foo.py, bar.robot"),
            )

            # Expect sorted output of glob results
            self.assertEqual(["bar.robot", "foo.py"], utils.process_glob_list_arg("*"))

            # Patterns that don't match any files
            self.assertEqual(
                ["*.bar", "x.y.z"], utils.process_glob_list_arg("*.bar, x.y.z")
            )

            # Recursive
            os.mkdir("subdir")
            filename = os.path.join("subdir", "baz.resource")
            touch(filename)
            self.assertEqual([filename], utils.process_glob_list_arg("**/*.resource"))

    def test_decode_to_unicode(self):
        self.assertEqual("\xfc", utils.decode_to_unicode(b"\xfc"))
        self.assertEqual("\u2603", utils.decode_to_unicode("\u2603"))
        self.assertEqual(None, utils.decode_to_unicode(None))


class TestMergedConfig(unittest.TestCase):
    def test_init(self):
        config = utils.merge_config(
            {
                "universal_config": {"hello": "world"},
                "user_config": {"hello": "christian"},
            }
        )
        self.assertEqual(config["hello"], "christian")

    def test_merge_failure(self):
        with self.assertRaises(ConfigMergeError) as cm:
            utils.merge_config(
                {
                    "universal_config": {"hello": "world", "test": {"sample": 1}},
                    "user_config": {"hello": "christian", "test": [1, 2]},
                }
            )
        exception = cm.exception
        self.assertEqual(exception.config_name, "user_config")


class TestDictMerger(unittest.TestCase):
    """some stuff that didnt get covered by usual usage"""

    def test_merge_into_list(self):
        combo = utils.dictmerge([1, 2], 3)
        self.assertSequenceEqual(combo, [1, 2, 3])

    def test_cant_merge_into_dict(self):
        with self.assertRaises(ConfigMergeError):
            utils.dictmerge({"a": "b"}, 2)

    def test_cant_merge_nonsense(self):
        with self.assertRaises(ConfigMergeError):
            utils.dictmerge(pytz, 2)


class TestProcessListOfPairsDictArg:
    def test_process_list_of_pairs_dict_arg__already_dict(self):
        expected_dict = {"foo": "bar"}
        actual_dict = utils.process_list_of_pairs_dict_arg(expected_dict)
        assert actual_dict is expected_dict

    def test_process_list_of_pairs_dict_arg__valid_values(self):
        valid_values = "foo:bar,baz:boo"
        actual_dict = utils.process_list_of_pairs_dict_arg(valid_values)
        assert actual_dict == {"foo": "bar", "baz": "boo"}

    def test_process_list_of_pairs_dict_arg__uri_values(self):
        uri_value = "companyWebsite:https://www.salesforce.org:8080"
        actual_dict = utils.process_list_of_pairs_dict_arg(uri_value)
        assert actual_dict == {"companyWebsite": "https://www.salesforce.org:8080"}

    def test_process_list_of_pairs_dict_arg__not_dict_or_string(self):
        unsupported = ("foo", "bar")
        error_message = re.escape(
            f"Arg is not a dict or string ({type(unsupported)}): {unsupported}"
        )
        with pytest.raises(TaskOptionsError, match=error_message):
            utils.process_list_of_pairs_dict_arg(unsupported)

    def test_process_list_of_pairs_dict_arg__not_name_value_pair(self):
        not_pair = "foo:bar,baz"
        error_message = re.escape("Var is not a name/value pair: baz")
        with pytest.raises(TaskOptionsError, match=error_message):
            utils.process_list_of_pairs_dict_arg(not_pair)

    def test_process_list_of_pairs_dict_arg__duplicate_value(self):
        duplicate = "foo:bar,foo:baz"
        error_message = re.escape("Var specified twice: foo")
        with pytest.raises(TaskOptionsError, match=error_message):
            utils.process_list_of_pairs_dict_arg(duplicate)
