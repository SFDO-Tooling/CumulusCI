import unittest
from TestListener import TestListener
import pytest


class TestTestListener(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.listener = TestListener()

    def test_reset_test_listener_keyword_cache(self):
        """Verify the internal cache is reset by the reset keyword"""

        # simulate what robot does when a keyword finishes executing
        self.listener._end_keyword("log", {"status": "PASS", "args": tuple()})

        self.listener.reset_test_listener_keyword_cache()
        assert len(self.listener.keyword_cache) == 0

    def test_reset_robot_log_cache(self):
        self.listener.log_messages.append("Danger Will Robinson!")
        self.listener.reset_robot_log_cache()
        assert len(self.listener.log_messages) == 0

    def test_assert_keyword_failure(self):
        self.listener.reset_test_listener_keyword_cache()
        with pytest.raises(
            Exception,
            match=r"No keyword with name 'bogus' with args '\('arg1', 'arg2'\)' was found",
        ):
            self.listener.assert_keyword_status("PASS", "bogus", "arg1", "arg2")

    def test_assert_keyword_pass(self):
        # simulate what robot does when a keyword finishes executing
        self.listener._end_keyword("log", {"status": "PASS", "args": tuple()})

        # should not raise an exception
        self.listener.assert_keyword_status("PASS", "log")
