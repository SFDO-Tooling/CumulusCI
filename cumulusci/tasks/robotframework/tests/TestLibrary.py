# from cumulusci.robotframework.utils import selenium_retry

# The following decorator is commented out, because with it the
# library gets two extra keywords. I'm not certain if that's what
# should be happening, or if those two keywords are actually just
# helper functions that are accidentially ending up as keywords


# @selenium_retry
class TestLibrary(object):
    """Documentation for the TestLibrary library."""

    def library_keyword_one(self):
        """Keyword documentation with *bold* and _italics_"""
        return "this is keyword one from TestLibrary.py"

    def library_keyword_two(self):
        return "this is keyword two from TestLibrary.py"
