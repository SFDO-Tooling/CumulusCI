from cumulusci.core import exceptions


class TestExceptions:
    def test_ApexCompilationException_str(self):
        err = exceptions.ApexCompilationException(42, "Too many braces")
        assert str(err) == "Apex compilation failed on line 42: Too many braces"

    def test_ApexException(self):
        err = exceptions.ApexException("Things got real", "Anon line 1")
        assert str(err) == "Apex error: Things got real\n  Stacktrace:\n  Anon line 1"
