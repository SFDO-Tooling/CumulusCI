import pytest
from TestListener import TestListener


class TestTestListener:
    @classmethod
    def setup_class(cls):
        cls.listener = TestListener()

    def test_reset_test_listener_keyword_log(self):
        """Verify the internal cache is reset by the reset keyword"""

        # simulate what robot does when a keyword finishes executing
        self.listener._end_keyword("log", {"status": "PASS", "args": tuple()})

        self.listener.reset_test_listener_keyword_log()
        assert len(self.listener.keyword_log) == 0

    def test_reset_test_listener_message_log(self):
        self.listener.message_log.append("Danger Will Robinson!")
        self.listener.reset_test_listener_message_log()
        assert len(self.listener.message_log) == 0

    def test_assert_keyword_failure(self):
        self.listener.reset_test_listener_keyword_log()
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
