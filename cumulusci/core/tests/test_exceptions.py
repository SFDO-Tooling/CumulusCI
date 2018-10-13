import unittest

from cumulusci.core import exceptions


class TestExceptions(unittest.TestCase):
    def test_ApexCompilationException_str(self):
        err = exceptions.ApexCompilationException(42, "Too many braces")
        self.assertEqual(
            "Apex compilation failed on line 42: Too many braces", str(err)
        )

    def test_ApexException(self):
        err = exceptions.ApexException("Things got real", "Anon line 1")
        self.assertEqual(
            "Apex error: Things got real\n  Stacktrace:\n  Anon line 1", str(err)
        )
