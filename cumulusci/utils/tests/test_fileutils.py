import doctest
from cumulusci.utils import fileutils
import responses


class TestFileutils:
    @responses.activate
    def test_fileutils(self):
        try:
            with responses.RequestsMock() as rsps:
                rsps.add("GET", "http://www.salesforce.com", body="<!DOCTYPE HTML ...")
                doctest.testmod(fileutils, raise_on_error=True, verbose=True)
        except doctest.DocTestFailure as e:
            print("Got")
            print(str(e.got))
            raise
